# -*- coding: utf-8 -*-

import pytest

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.pytester import Testdir


SUMMARY_LINES = [
    '--------------------------- snapshot report summary ----------------------------',
    '',
    '=========================== short test summary info ============================',
]


@pytest.fixture(autouse=True)
def makeconfig(testdir: 'Testdir') -> None:
    testdir.makefile('.json', pyrightconfig=json.dumps({'typeCheckingMode': 'strict'}))


def test_collection(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/example.py': '', 'typesafety/foo/foo.py': ''})

    result = testdir.runpytest('--collect-only')
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


def test_reveal_type(testdir: 'Testdir') -> None:
    content = '''
    from typing import Union

    def foo(a: Union[int, str]) -> None:
        if isinstance(a, str):
            reveal_type(a)  # T: str
        else:
            reveal_type(a)  # T: int
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_reveal_type_incorrect_comment(testdir: 'Testdir') -> None:
    content = '''
    def foo(a: str) -> None:
        reveal_type(a)  # T: int
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | def foo(a: str) -> None:',
            '2 |     reveal_type(a)  # T: int',
            'E | Expected revealed type to be "int" but got "str" instead',
            *SUMMARY_LINES,
        ],
        consecutive=True,
    )


def test_reveal_type_missing_comment(testdir: 'Testdir') -> None:
    content = '''
    def foo(a: str) -> None:
        reveal_type(a)
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | def foo(a: str) -> None:',
            '2 |     reveal_type(a)',
            'E | Missing type comment, revealed type: str',
            *SUMMARY_LINES,
        ],
        consecutive=True,
    )


def test_error_message(testdir: 'Testdir') -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))  # E: "split" is not a known member of "None"
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_error_message_comment_no_error(testdir: 'Testdir') -> None:
    content = '''
    from typing import Optional

    def foo(a: str) -> None:
        print(a.split('.'))  # E: "split" is not a known member of "None"
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | from typing import Optional',
            '2 | ',
            '3 | def foo(a: str) -> None:',
            '4 |     print(a.split(\'.\'))  # E: "split" is not a known member of "None"',
            'E | Did not raise an error',
            *SUMMARY_LINES,
        ],
        consecutive=True,
    )
    assert 'pytest_pyright.plugin.PyrightError' not in result.stdout.str()


def test_error_message_missing(testdir: 'Testdir') -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | from typing import Optional',
            '2 | ',
            '3 | def foo(a: Optional[str]) -> None:',
            '4 |     print(a.split(\'.\'))',
            'E | Unexpected error: "split" is not a known member of "None"',
            *SUMMARY_LINES,
        ],
        consecutive=True,
    )
    assert 'pytest_pyright.plugin.PyrightError' not in result.stdout.str()


def test_unexpected_error_first_line(testdir: 'Testdir') -> None:
    content = '''
    from bad_module import foo
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            '1 | from bad_module import foo',
            'E | Unexpected error: Import "bad_module" could not be resolved',
            *SUMMARY_LINES,
        ],
        consecutive=True,
    )


def test_multiple_errors(testdir: 'Testdir') -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
        if a is not None:
            reveal_type(a)
    '''
    testdir.makepyfile(**{'typesafety/bar.py': content})
    result = testdir.runpytest()
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
            *SUMMARY_LINES,
        ],
        consecutive=True,
    )


def test_custom_pyright_directory_commandline(testdir: 'Testdir') -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
    '''
    testdir.makepyfile(**{'my_pyright_tests/bar.py': content})
    result = testdir.runpytest('--collect-only')
    assert result.parseoutcomes() == {}

    result = testdir.runpytest('--pyright-dir=my_pyright_tests', '--collect-only')
    assert result.parseoutcomes() == {'test': 1}


def test_custom_pyright_directory_commandline_multiple_parts(
    testdir: 'Testdir',
) -> None:
    content = '''
    from typing import Optional

    def foo(a: Optional[str]) -> None:
        print(a.split('.'))
    '''
    testdir.makepyfile(**{'custom_typesafety/pyright/bar.py': content})
    result = testdir.runpytest('--collect-only')
    assert result.parseoutcomes() == {}

    result = testdir.runpytest(
        '--pyright-dir=custom_typesafety/pyright', '--collect-only'
    )
    assert result.parseoutcomes() == {'test': 1}
