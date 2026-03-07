from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """
    Базовая модель регистратора.

    Лишние поля запрещаем, чтобы формат манифестов был строгим
    и не расползался со временем.
    """

    model_config = ConfigDict(extra="forbid")


class ValueTypeManifest(StrictModel):
    """
    Описание Python-типа параметра или входного аргумента.
    """

    kind: Literal["str", "int", "float", "bool", "path", "enum", "list", "unknown"]
    display_name: str
    enum_values: list[Any] = Field(default_factory=list)


class InputRuleManifest(StrictModel):
    """
    Описание одного атомарного правила выбора.

    Например:
    - одно изображение;
    - несколько txt-файлов;
    - пользовательский набор расширений.
    """

    kind: str
    multiple: bool
    extensions: list[str] = Field(default_factory=list)


class InputArgumentManifest(StrictModel):
    """
    Входной аргумент скрипта или метода сервиса.
    """

    name: str
    value_type: ValueTypeManifest
    rules: list[InputRuleManifest]


class ParamArgumentManifest(StrictModel):
    """
    Настраиваемый параметр скрипта или сервиса.
    """

    name: str
    value_type: ValueTypeManifest
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


class OneshotScriptManifest(StrictModel):
    """
    Полное описание зарегистрированного oneshot-скрипта.
    """

    kind: Literal["oneshot_script"] = "oneshot_script"
    id: str
    explicit_id: str | None = None
    source_file: str
    relative_path: str
    qualname: str
    title: str
    description: str | None = None
    icon: str | None = None
    timeout: int | None = None
    inputs: list[InputArgumentManifest] = Field(default_factory=list)
    params: list[ParamArgumentManifest] = Field(default_factory=list)
    supports_direct_run: bool = False


class ServiceScriptManifest(StrictModel):
    """
    Описание одного метода сервиса, который становится пунктом меню.
    """

    kind: Literal["service_script"] = "service_script"
    id: str
    explicit_id: str | None = None
    service_id: str
    service_qualname: str
    source_file: str
    relative_path: str
    qualname: str
    method_name: str
    title: str
    description: str | None = None
    icon: str | None = None
    timeout: int | None = None
    inputs: list[InputArgumentManifest] = Field(default_factory=list)
    params: list[ParamArgumentManifest] = Field(default_factory=list)
    supports_direct_run: bool = False


class ServiceManifest(StrictModel):
    """
    Полное описание сервиса.
    """

    kind: Literal["service"] = "service"
    id: str
    explicit_id: str | None = None
    source_file: str
    relative_path: str
    qualname: str
    title: str
    description: str | None = None
    icon: str | None = None
    timeout: int | None = None
    max_downtime: int | None = None
    on_startup: bool = False
    init_params: list[ParamArgumentManifest] = Field(default_factory=list)
    scripts: list[ServiceScriptManifest] = Field(default_factory=list)


class ModuleInspectionResult(StrictModel):
    """
    Результат анализа одного Python-файла из папки scripts.
    """

    source_file: str
    relative_path: str
    file_hash_sha256: str
    dependencies: list[str] = Field(default_factory=list)
    oneshot_scripts: list[OneshotScriptManifest] = Field(default_factory=list)
    services: list[ServiceManifest] = Field(default_factory=list)

    @property
    def has_definitions(self) -> bool:
        """
        Есть ли в файле хоть одна зарегистрированная сущность.
        """
        return bool(self.oneshot_scripts or self.services)
