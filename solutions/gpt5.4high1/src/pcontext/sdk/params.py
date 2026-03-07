from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """
    Описание настраиваемого параметра скрипта или сервиса.

    Экземпляр этого класса кладётся в Annotated[..., Param(...)].
    Затем регистратор прочитает его и построит схему параметров для UI.
    """

    default: Any
    title: str | None = None
    description: str | None = None
    ge: float | None = None
    gt: float | None = None
    le: float | None = None
    lt: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None


def Param(
    default: Any,
    *,
    title: str | None = None,
    description: str | None = None,
    ge: float | None = None,
    gt: float | None = None,
    le: float | None = None,
    lt: float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
) -> ParamSpec:
    """
    Создаёт описание параметра, которое затем используется в `typing.Annotated`.

    Пример:
        threshold: Annotated[float, Param(0.5, ge=0.0, le=1.0)]
    """
    if min_length is not None and min_length < 0:
        raise ValueError("Параметр min_length не может быть отрицательным.")

    if max_length is not None and max_length < 0:
        raise ValueError("Параметр max_length не может быть отрицательным.")

    if min_length is not None and max_length is not None and min_length > max_length:
        raise ValueError("Параметр min_length не может быть больше max_length.")

    if ge is not None and gt is not None:
        raise ValueError("Нельзя одновременно указывать ge и gt.")

    if le is not None and lt is not None:
        raise ValueError("Нельзя одновременно указывать le и lt.")

    if ge is not None and le is not None and ge > le:
        raise ValueError("Параметр ge не может быть больше le.")

    if gt is not None and lt is not None and gt >= lt:
        raise ValueError("Параметр gt должен быть меньше lt.")

    return ParamSpec(
        default=default,
        title=title,
        description=description,
        ge=ge,
        gt=gt,
        le=le,
        lt=lt,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
    )