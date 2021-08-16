from typing import TypedDict


class Data(TypedDict, total=False):
    points: int


def data_handler(data: Data) -> None:
    points = data.get('points')
    reveal_type(points)  # T: int | None

    points = data.get('points', 0)
    reveal_type(points)  # T: int

    # as we specified total=False in the Data type, the points key might be missing
    print(data['points'])  # E: Could not access item in TypedDict
