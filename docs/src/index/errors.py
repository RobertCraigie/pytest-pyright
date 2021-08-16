from typing import Optional


def main(string: Optional[str]) -> None:
    print(string.split('.'))  # E: "split" is not a known member of "None"
