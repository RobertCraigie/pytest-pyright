# -*- coding: utf-8 -*-

import pytest

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.pytester import Testdir


@pytest.fixture(autouse=True)
def makeconfig(testdir: 'Testdir') -> None:
    testdir.makefile('.json', pyrightconfig=json.dumps({'typeCheckingMode': 'strict'}))


def test_collection(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/example.py': '', 'typesafety/foo/foo.py': ''})

    result = testdir.runpytest('--collect-only')
    outcomes = result.parseoutcomes()
    assert outcomes['tests'] == 2

    result.stdout.fnmatch_lines([
        '*<PyrightTestFile typesafety/example.py>*',
        '*<PyrightTestItem example.py>*',
        '*<PyrightTestFile typesafety/foo/foo.py>*',
        '*<PyrightTestItem foo.py>*',
    ])

    assert result.ret == 0


def test_reveal_type(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/bar.py': '''
        from typing import Union

        def foo(a: Union[int, str]) -> None:
            if isinstance(a, str):
                reveal_type(a)  # T: str
            else:
                reveal_type(a)  # T: int
    '''})

    result = testdir.runpytest()  # noqa
    result.assert_outcomes(passed=1)


def test_reveal_type_incorrect_comment(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/bar.py': '''
        def foo(a: str) -> None:
            reveal_type(a)  # T: int
    '''})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([
        '*Expected revealed type on line 2 to be "int" but got "str" instead',
    ])
    assert 'pytest_pyright.plugin.PyrightError' in result.stdout.str()


def test_reveal_type_missing_comment(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/bar.py': '''
        def foo(a: str) -> None:
            reveal_type(a)
    '''})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([
        '*Missing type comment on line: 2, revealed type: str',
    ])
    assert 'pytest_pyright.plugin.PyrightError' in result.stdout.str()


def test_error_message(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/bar.py': '''
        from typing import Optional

        def foo(a: Optional[str]) -> None:
            print(a.split('.'))  # E: "split" is not a known member of "None"
    '''})
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_error_message_comment_no_error(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/bar.py': '''
        from typing import Optional

        def foo(a: str) -> None:
            print(a.split('.'))  # E: "split" is not a known member of "None"
    '''})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([
        '*Did not raise an error on line: 4',
    ])
    assert 'pytest_pyright.plugin.PyrightError' in result.stdout.str()


def test_error_message_missing(testdir: 'Testdir') -> None:
    testdir.makepyfile(**{'typesafety/bar.py': '''
        from typing import Optional

        def foo(a: Optional[str]) -> None:
            print(a.split('.'))
    '''})
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([
        '*Unexpected error on line 4: "split" is not a known member of "None"',
    ])
    assert 'pytest_pyright.plugin.PyrightError' in result.stdout.str()
