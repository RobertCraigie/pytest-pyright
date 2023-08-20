# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.pytester import Pytester


@pytest.fixture(autouse=True)
def makeconfig(pytester: Pytester) -> None:
    pytester.makefile('.json', pyrightconfig=json.dumps({'typeCheckingMode': 'strict'}))


def test_collection(pytester: Pytester) -> None:
    pytester.makepyfile(**{'typesafety/example.py': '', 'typesafety/foo/foo.py': ''})

    result = pytester.runpytest('--collect-only')
    outcomes = result.parseoutcomes()
    assert outcomes['tests'] == 2

    result.stdout.fnmatch_lines(
        [
            '*<PyrightTestFile typesafety/example.py>*',
            '*<PyrightTestItem example.py>*',
            '*<PyrightTestFile typesafety/foo/foo.py>*',
            '*<PyrightTestItem foo.py>*',
        ]
    )

    assert result.ret == 0


def test_reveal_type(pytester: Pytester) -> None:
    content = '''
    from typing import Union

    def foo(a: Union[int, str]) -> None:
        if isinstance(a, str):
            reveal_type(a)  # T: str
        else:
            reveal_type(a)  # T: int
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_reveal_type_incorrect_comment(pytester: Pytester) -> None:
    content = '''
    def foo(a: str) -> None:
        reveal_type(a)  # T: int
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | def foo(a: str) -> None:',
            '2 |     reveal_type(a)  # T: int',
            'E | Expected revealed type to be "int" but got "str" instead',
        ],
        consecutive=True,
    )


def test_reveal_type_missing_comment(pytester: Pytester) -> None:
    content = '''
    def foo(a: str) -> None:
        reveal_type(a)
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | def foo(a: str) -> None:',
            '2 |     reveal_type(a)',
            'E | Missing type comment, revealed type: str',
        ],
        consecutive=True,
    )


def test_error_message(pytester: Pytester) -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))  # E: "split" is not a known member of "None"
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_error_message_comment_no_error(pytester: Pytester) -> None:
    content = '''
    from typing import Optional

    def foo(a: str) -> None:
        print(a.split('.'))  # E: "split" is not a known member of "None"
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | from typing import Optional',
            '2 | ',
            '3 | def foo(a: str) -> None:',
            '4 |     print(a.split(\'.\'))  # E: "split" is not a known member of "None"',
            'E | Did not raise an error',
        ],
        consecutive=True,
    )
    assert 'pytest_pyright.plugin.PyrightError' not in result.stdout.str()


def test_error_message_missing(pytester: Pytester) -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | from typing import Optional',
            '2 | ',
            '3 | def foo(a: Optional[str]) -> None:',
            '4 |     print(a.split(\'.\'))',
            'E | Unexpected error: "split" is not a known member of "None"',
        ],
        consecutive=True,
    )
    assert 'pytest_pyright.plugin.PyrightError' not in result.stdout.str()


def test_unexpected_error_first_line(pytester: Pytester) -> None:
    content = '''
    from bad_module import foo
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | from bad_module import foo',
            'E | Unexpected error: Import "bad_module" could not be resolved',
        ],
        consecutive=True,
    )


def test_multiple_errors(pytester: Pytester) -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
        if a is not None:
            reveal_type(a)
    '''
    pytester.makepyfile(**{'typesafety/bar.py': content})
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | from typing import Optional',
            '2 | ',
            '3 | def foo(a: Optional[str]) -> None:',
            '4 |     print(a.split(\'.\'))',
            'E | Unexpected error: "split" is not a known member of "None"',
            '5 |     if a is not None:',
            '6 |         reveal_type(a)',
            'E | Missing type comment, revealed type: str',
        ],
        consecutive=True,
    )


def test_custom_pyright_directory_commandline(pytester: Pytester) -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
    '''
    pytester.makepyfile(**{'my_pyright_tests/bar.py': content})
    result = pytester.runpytest('--collect-only')
    assert result.parseoutcomes() == {}

    result = pytester.runpytest('--pyright-dir=my_pyright_tests', '--collect-only')
    assert result.parseoutcomes() == {'test': 1}


def test_custom_pyright_directory_commandline_multiple_parts(
    pytester: Pytester,
) -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
    '''
    pytester.makepyfile(**{'custom_typesafety/pyright/bar.py': content})
    result = pytester.runpytest('--collect-only')
    assert result.parseoutcomes() == {}

    result = pytester.runpytest(
        '--pyright-dir=custom_typesafety/pyright', '--collect-only'
    )
    assert result.parseoutcomes() == {'test': 1}
