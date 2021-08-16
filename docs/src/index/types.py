from typing import Union


def main(string_or_int: Union[str, int]) -> None:
    if isinstance(string_or_int, str):
        reveal_type(string_or_int)  # T: str
    else:
        reveal_type(string_or_int)  # T: int
