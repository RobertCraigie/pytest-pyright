from syrupy.assertion import SnapshotAssertion
from pytest_pyright.plugin import PyrightErrors, PyrightError, PyrightTerminalRepr


class MockedItem:
    def __init__(self, content: str) -> None:
        self.content = content


def create_formatter(*errors: PyrightError, content: str) -> PyrightTerminalRepr:
    return PyrightTerminalRepr.from_errors(
        PyrightErrors(
            list(errors),
            item=MockedItem(content=content),  # type: ignore
        )
    )


def test_small_file(snapshot: SnapshotAssertion) -> None:
    content = """
    def foo() -> None:
        print(b)
    """
    writer = create_formatter(
        PyrightError('Unexpected error: "b" is not defined', lineno=3), content=content
    )
    assert str(writer) == snapshot


def test_large_file(snapshot: SnapshotAssertion) -> None:
    content = 'def foo() -> None:'
    content += '\n' * 100 + 'print(a)'
    writer = create_formatter(
        PyrightError('Unexpected error: "a" is not defined', lineno=101),
        content=content,
    )
    assert str(writer) == snapshot
