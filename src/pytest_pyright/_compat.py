from __future__ import annotations

from typing import TypeVar

import pydantic
from pydantic import BaseModel


_ModelT = TypeVar('_ModelT', bound=BaseModel)


PYDANTIC_V2 = pydantic.VERSION.startswith('2.')


def model_rebuild(model: type[BaseModel]) -> None:
    if PYDANTIC_V2:
        model.model_rebuild()
    else:
        model.update_forward_refs()  # pyright: ignore[reportDeprecated]


def model_parse_json(model: type[_ModelT], obj: str | bytes) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_validate_json(obj)
    else:
        return model.parse_raw(obj)  # type: ignore
