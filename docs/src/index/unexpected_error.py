from typing import TypedDict


class Data(TypedDict, total=False):
    points: int


def data_handler(data: Data) -> None:
    # remove this line and the following comment and run `make docs-tests`
    print(data['points'])  # E: Could not access item in TypedDict
