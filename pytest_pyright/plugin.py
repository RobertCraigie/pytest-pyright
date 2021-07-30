# -*- coding: utf-8 -*-

import re
import sys
import subprocess
from pathlib import Path
from typing import Optional, Union, Iterator, Any, cast, TYPE_CHECKING

import pytest
from py._path.local import LocalPath

from _pytest.nodes import Node
from _pytest.config import Config
from _pytest._io import TerminalWriter
from _pytest._code import ExceptionInfo
from _pytest._code.code import TerminalRepr, ReprEntry, ReprFileLocation

from .models import PyrightResult, PyrightFile

if TYPE_CHECKING:
    from _pytest._code.code import _TracebackStyle
    from _pytest.config.argparsing import Parser


# TODO: better diffs
# TODO: cleanup code
# TODO: improve performance
# TODO: ini option for custom typesafety
# TODO: add support for multi-line errors
# TODO: add option to display pyright output

PYRIGHT_TYPE_RE = re.compile(r'Type of "(.*)" is "(?P<type>.*)"')


def relative_path(path: LocalPath) -> Path:
    return Path(path).relative_to(Path.cwd())


def is_typesafety_file(parent: Node, path: LocalPath) -> bool:
    # TODO: don't know how good this check is
    relative = relative_path(path)
    return relative.as_posix().startswith(parent.config.option.pyright_dir)


def pytest_collect_file(path: LocalPath, parent: Node) -> Optional['PyrightTestFile']:
    if path.ext == '.py' and is_typesafety_file(parent, path):
        return PyrightTestFile.from_parent(parent, fspath=path)

    return None


def pytest_addoption(parser: 'Parser'):
    group = parser.getgroup('pyright')
    group.addoption(
        '--pyright-dir',
        action='store',
        default='typesafety',
        help='Specify the root directory to use to search for pyright tests.'
    )


class TraceLastReprEntry(ReprEntry):
    def toterminal(self, tw: TerminalWriter) -> None:
        if not self.reprfileloc:
            return

        self.reprfileloc.toterminal(tw)
        for line in self.lines:
            red = line.startswith('E   ')
            tw.line(line, bold=True, red=red)

        return


class PyrightError(AssertionError):
    def __init__(self, error_message: Optional[str] = None, lineno: int = 0) -> None:
        self.error_message = error_message or ''
        self.lineno = lineno
        super().__init__()

    def __str__(self) -> str:
        return self.error_message


class PyrightTestItem(pytest.Item):
    def __init__(
        self,
        name: str,
        parent: Optional['PyrightTestFile'] = None,
        config: Optional[Config] = None,
        *,
        path: Path,
    ) -> None:
        super().__init__(name, parent, config)
        self.path = path
        self.starting_lineno = 1

    def runtest(self) -> None:
        file = PyrightFile.parse(self.path)
        process = subprocess.run(
            [
                'pyright',
                f'--project={self.path.parent}',
                '--outputjson',
                str(self.path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # https://github.com/microsoft/pyright/blob/main/docs/command-line.md#pyright-exit-codes
        if process.returncode in {2, 3, 4}:
            print(process.stderr.decode('utf-8', file=sys.stderr))
            print(process.stdout.decode('utf-8'))
            raise PyrightError('')

        result = PyrightResult.parse_raw(process.stdout)
        absolute = str(self.path.absolute())

        for diagnostic in result.diagnostics:
            if diagnostic.file != absolute:
                raise PyrightError(
                    f'Received diagnostic for unknown file: {diagnostic.file}'
                )

            # pyright json diagnostic line numbers are 0-based
            line = diagnostic.range.start.line + 1

            if diagnostic.severity == 'error':
                # we only care about the first line
                actual, *_ = diagnostic.message.split('\n')

                try:
                    expected = file.get_error(line)
                except KeyError:
                    raise PyrightError(
                        f'Unexpected error on line {line}: {actual}', lineno=line
                    ) from None

                if expected != actual:
                    raise PyrightError(
                        f'Expected type error on line {line} to be "{expected}" but got "{actual}" instead',
                        lineno=line,
                    )
            elif diagnostic.severity == 'information':
                match = PYRIGHT_TYPE_RE.match(diagnostic.message)
                if match is None:
                    raise PyrightError(
                        f'Could not extract type from message: "{diagnostic.message}" on line: {line}',
                        lineno=line,
                    )

                actual = match.group('type')

                try:
                    expected = file.get_information(line)
                except KeyError:
                    raise PyrightError(
                        f'Missing type comment on line: {line}, revealed type: {actual}',
                        lineno=line,
                    ) from None

                if expected != actual:
                    raise PyrightError(
                        f'Expected revealed type on line {line} to be "{expected}" but got "{actual}" instead',
                        lineno=line,
                    )
            else:
                raise PyrightError(
                    f'Unknown diagnostic type: {diagnostic.severity}', lineno=line
                )

        for line, error in file.errors.items():
            if not error.accessed:
                raise PyrightError(
                    f'Did not raise an error on line: {line}', lineno=line
                )

    def repr_failure(
        self,
        excinfo: ExceptionInfo[BaseException],
        style: Optional['_TracebackStyle'] = None,
    ) -> Union[str, TerminalRepr]:
        """Remove unnecessary error traceback if applicable

        this method is taken directly from pytest-mypy-plugins along with
        related classes, e.g. TraceLastReprEntry
        """
        # NOTE: I do not know how much of this code is required / functioning as expected
        if excinfo.errisinstance(SystemExit):
            # We assume that before doing exit() (which raises SystemExit) we've printed
            # enough context about what happened so that a stack trace is not useful.
            return excinfo.exconly(tryshort=True)

        if excinfo.errisinstance(PyrightError):
            # with traceback removed
            excinfo = cast(ExceptionInfo[PyrightError], excinfo)
            exception_repr = excinfo.getrepr(style='short')
            exception_repr.reprcrash.message = ''  # type: ignore
            repr_file_location = (
                ReprFileLocation(  # pyright: reportGeneralTypeIssues=false
                    path=self.fspath,
                    lineno=self.starting_lineno + excinfo.value.lineno,
                    message='',
                )
            )
            repr_tb_entry = TraceLastReprEntry(
                exception_repr.reprtraceback.reprentries[-1].lines[1:],
                None,
                None,
                repr_file_location,
                'short',
            )
            exception_repr.reprtraceback.reprentries = [repr_tb_entry]
            return exception_repr

        return super().repr_failure(excinfo, style='native')


class PyrightTestFile(pytest.File):
    @classmethod
    def from_parent(
        cls, *args: Any, **kwargs: Any
    ) -> 'PyrightTestFile':  # pyright: reportIncompatibleMethodOverride=false
        return cast(
            PyrightTestFile,
            super().from_parent(*args, **kwargs),
        )

    def collect(self) -> Iterator[PyrightTestItem]:
        path = Path(self.fspath)
        yield PyrightTestItem.from_parent(parent=self, name=path.name, path=path)
