# -*- coding: utf-8 -*-

import re
import sys
import subprocess
from pathlib import Path
from functools import lru_cache
from typing import Optional, List, Union, Iterator, Any, cast, TYPE_CHECKING

import pytest
import pyright

from _pytest.nodes import Node
from _pytest.config import Config
from _pytest._io import TerminalWriter
from _pytest._code import ExceptionInfo
from _pytest._code.code import TerminalRepr

from .models import PyrightResult, PyrightFile
from ._compat import model_parse_json

if TYPE_CHECKING:
    from _pytest._code.code import _TracebackStyle
    from _pytest.config.argparsing import Parser


# TODO: cleanup code
# TODO: improve performance
# TODO: ini option for custom dir
# TODO: add support for multi-line errors
# TODO: add support for multiple errors on the same line
# TODO: check for unaccessed type information

PYRIGHT_TYPE_RE = re.compile(r'Type of "(.*)" is "(?P<type>.*)"')


def relative_path(path: Path) -> Path:
    return path.relative_to(Path.cwd())


def is_typesafety_file(parent: Node, path: Path) -> bool:
    # TODO: don't know how good this check is
    relative = relative_path(path)
    return relative.as_posix().startswith(parent.config.option.pyright_dir)


def maybe_decode(data: Union[bytes, str]) -> str:
    if isinstance(data, (bytes, bytearray)):
        return data.decode('utf-8')
    if isinstance(data, memoryview):
        raise TypeError(f'Unexpected type: {type(data)}')
    return data


def pytest_collect_file(file_path: Path, parent: Node) -> Optional['PyrightTestFile']:
    if file_path.suffix == '.py' and is_typesafety_file(parent, file_path):
        return PyrightTestFile.from_parent(parent, path=file_path)
    return None


def pytest_addoption(parser: 'Parser'):
    group = parser.getgroup('pyright')
    group.addoption(
        '--pyright-dir',
        action='store',
        default='typesafety',
        help='Specify the root directory to use to search for pyright tests.',
    )


class PyrightTerminalRepr(TerminalRepr):
    def __init__(self, lines: List[str]) -> None:
        self.lines = lines

    def toterminal(self, tw: TerminalWriter) -> None:
        for line in self.lines:
            red = line.startswith('E')
            tw.line(line, bold=red, red=red)

    @classmethod
    def from_error(cls, error: 'PyrightError') -> 'PyrightTerminalRepr':
        return cls(lines=[f'E |  {error.message}'])

    @classmethod
    def from_errors(cls, exc: 'PyrightErrors') -> 'PyrightTerminalRepr':
        """Build a Repr that outputs something like the following

        1 | from typing import Optional
        2 | def foo(a: Optional[str] = None) -> None:
        3 |     a.split('.')
        E | "split" is not a known member of "None"
        """
        # TODO: cleanup
        # TODO: add carets to show where the error ocurred

        def get_separator(lineno: int) -> str:
            return '|'.rjust(max_padding - num_digits(lineno) + 1)

        def num_digits(num: int) -> int:
            # NOTE: this assumes a positive number
            return len(str(num))

        content_lines = exc.item.content.splitlines()
        max_padding = num_digits(len(content_lines)) + 1
        lines = [
            f'{lineno}{get_separator(lineno)} {content}'
            for lineno, content in enumerate(content_lines, start=1)
        ]

        separator = '|'.rjust(max_padding)
        for offset, error in enumerate(
            sorted(exc.errors, key=lambda e: e.lineno), start=0
        ):
            lines.insert(error.lineno + offset, f'E{separator} {error.message}')

        return cls(lines=lines)


class PyrightError(AssertionError):
    def __init__(self, message: str, lineno: int = 0) -> None:
        self.message = message
        self.lineno = lineno
        super().__init__()

    def __str__(self) -> str:
        return self.message


class PyrightErrors(Exception):
    def __init__(self, errors: List[PyrightError], item: 'PyrightTestItem') -> None:
        self.item = item
        self.errors = errors


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
        file = PyrightFile.parse(self.content)
        process = pyright.run(
            f'--project={self.path.parent}',
            '--outputjson',
            str(self.path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # https://github.com/microsoft/pyright/blob/main/docs/command-line.md#pyright-exit-codes
        if process.returncode not in {0, 1}:
            print(maybe_decode(process.stderr), file=sys.stderr)
            print(maybe_decode(process.stdout))
            raise PyrightError(
                'An unknown error ocurred while running pyright, '
                'see the captured output for more details.'
            )

        result = model_parse_json(PyrightResult, process.stdout)
        absolute = str(self.path.absolute())
        errors: List[PyrightError] = []

        for diagnostic in result.diagnostics:
            if diagnostic.file != absolute:
                raise PyrightError(
                    f'Received diagnostic for unknown file: {diagnostic.file}; Expected {absolute}'
                )

            # pyright json diagnostic line numbers are 0-based
            line = diagnostic.range.start.line + 1

            if diagnostic.severity == 'error':
                # we only care about the first line
                actual, *_ = diagnostic.message.split('\n')

                try:
                    expected = file.get_error(line)
                except KeyError:
                    errors.append(
                        PyrightError(f'Unexpected error: {actual}', lineno=line)
                    )
                    continue

                if expected != actual:
                    errors.append(
                        PyrightError(
                            f'Expected type error to be \'{expected}\' but '
                            f'got \'{actual}\' instead',
                            lineno=line,
                        )
                    )
                    continue
            elif diagnostic.severity == 'information':
                match = PYRIGHT_TYPE_RE.match(diagnostic.message)
                if match is None:
                    errors.append(
                        PyrightError(
                            f'Could not extract type from message: "{diagnostic.message}"',
                            lineno=line,
                        )
                    )
                    continue

                actual = match.group('type')

                try:
                    expected = file.get_information(line)
                except KeyError:
                    errors.append(
                        PyrightError(
                            f'Missing type comment, revealed type: {actual}',
                            lineno=line,
                        )
                    )
                    continue

                if expected != actual:
                    errors.append(
                        PyrightError(
                            f'Expected revealed type to be "{expected}" but got "{actual}" instead',
                            lineno=line,
                        )
                    )
                    continue
            else:
                errors.append(
                    PyrightError(
                        f'Unknown diagnostic type: {diagnostic.severity}', lineno=line
                    )
                )

        for line, error in file.errors.items():
            if not error.accessed:
                errors.append(PyrightError('Did not raise an error', lineno=line))

        if errors:
            raise PyrightErrors(errors, item=self)

    def repr_failure(
        self,
        excinfo: ExceptionInfo[BaseException],
        style: Optional['_TracebackStyle'] = None,
    ) -> Union[str, TerminalRepr]:
        if isinstance(excinfo.value, PyrightError):
            return PyrightTerminalRepr.from_error(excinfo.value)

        if isinstance(excinfo.value, PyrightErrors):
            return PyrightTerminalRepr.from_errors(excinfo.value)

        return super().repr_failure(excinfo, style=style)

    def reportinfo(self):
        return self.fspath, 0, f'pyright: {self.name}'

    # TODO: does this cache get deleted when the item is destroyed?
    @property
    @lru_cache(maxsize=None)
    def content(self) -> str:
        return self.path.read_text()


class PyrightTestFile(pytest.File):
    @classmethod
    def from_parent(
        cls, *args: Any, **kwargs: Any
    ) -> 'PyrightTestFile':  # pyright: ignore[reportIncompatibleMethodOverride]
        return cast(
            PyrightTestFile,
            super().from_parent(*args, **kwargs),
        )

    def collect(self) -> Iterator[PyrightTestItem]:
        path = Path(self.fspath)
        yield PyrightTestItem.from_parent(parent=self, name=path.name, path=path)
