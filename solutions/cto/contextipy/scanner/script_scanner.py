"""Utilities for scanning script files within the Contextipy project."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

SUPPORTED_DECORATORS = {"oneshot_script", "service", "service_script"}


@dataclass(frozen=True, slots=True)
class ScanError:
    """Represents an error encountered while scanning a script file."""

    path: Path
    message: str


@dataclass(frozen=True, slots=True)
class ScannedScript:
    """Metadata discovered for a single script or service definition."""

    identifier: str
    kind: str
    title: str
    description: str
    docstring: str | None
    file_path: Path
    module: str
    qualname: str
    group: tuple[str, ...]
    accepts: tuple[str, ...]
    timeout: float | None
    related_service_id: str | None
    icon: str | None
    categories: tuple[str, ...]
    file_hash: str
    parameters: tuple[str, ...] = field(default_factory=tuple)

    @property
    def script_id(self) -> str:
        """Alias for the identifier to maintain backwards compatibility."""

        return self.identifier


@dataclass(frozen=True, slots=True)
class ScanResult:
    """The outcome of a scanning pass."""

    scripts: tuple[ScannedScript, ...]
    errors: tuple[ScanError, ...]

    def successful(self) -> bool:
        return not self.errors


class ScriptScanError(RuntimeError):
    """Raised when a script file cannot be processed."""


class ScriptScanner:
    """Scanner that inspects directories for Contextipy script definitions."""

    def __init__(self, roots: Iterable[Path] | Path) -> None:
        if isinstance(roots, Path):
            self._roots = (roots,)
        else:
            self._roots = tuple(roots)

    @property
    def roots(self) -> tuple[Path, ...]:
        return self._roots

    def scan(self) -> ScanResult:
        scripts: list[ScannedScript] = []
        errors: list[ScanError] = []
        for file_path in self._discover():
            try:
                scripts.extend(self._scan_file(file_path))
            except ScriptScanError as exc:
                errors.append(ScanError(file_path, str(exc)))
        return ScanResult(tuple(scripts), tuple(errors))

    def _discover(self) -> Iterator[Path]:
        for root in self._roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.py")):
                if path.name == "__init__.py":
                    continue
                yield path

    def _scan_file(self, path: Path) -> list[ScannedScript]:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - filesystem error
            raise ScriptScanError(f"Unable to read file: {exc}")

        try:
            module = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise ScriptScanError(f"Syntax error: {exc.msg} (line {exc.lineno})")

        module_icon, module_categories = _extract_module_metadata(module)
        file_hash = compute_file_hash(path)
        scripts: list[ScannedScript] = []
        for node in module.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                decorator_call = _select_decorator(node.decorator_list)
                if decorator_call is None:
                    continue
                try:
                    scripts.append(
                        _build_metadata(
                            node,
                            decorator_call,
                            path,
                            self._qualify(path),
                            module_icon,
                            module_categories,
                            file_hash,
                        )
                    )
                except ValueError as exc:
                    raise ScriptScanError(str(exc))
        return scripts

    def _qualify(self, path: Path) -> tuple[str, tuple[str, ...]]:
        root, relative = _split_root(path, self._roots)
        module = relative.with_suffix("")
        parts = module.parts
        if not parts:
            module_name = module.name
        else:
            module_name = ".".join(parts)
        group = parts[:-1]
        return module_name, group


def compute_file_hash(path: Path) -> str:
    """Return the SHA-256 hash of the given file."""

    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_scripts(roots: Iterable[Path] | Path) -> ScanResult:
    """Convenience wrapper around :class:`ScriptScanner`."""

    scanner = ScriptScanner(roots)
    return scanner.scan()


def _split_root(path: Path, roots: Sequence[Path]) -> tuple[Path, Path]:
    for root in roots:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        return root, relative
    return path.parent, Path(path.name)


def _select_decorator(decorators: Sequence[ast.expr]) -> ast.Call | None:
    for decorator in decorators:
        if isinstance(decorator, ast.Call):
            name = _decorator_name(decorator.func)
            if name in SUPPORTED_DECORATORS:
                return decorator
    return None


def _decorator_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _extract_module_metadata(module: ast.Module) -> tuple[str | None, tuple[str, ...]]:
    icon: str | None = None
    categories: list[str] = []
    for entry in module.body:
        if isinstance(entry, ast.Assign) and entry.targets:
            target = entry.targets[0]
            if isinstance(target, ast.Name):
                if target.id in {"ICON", "__icon__"}:
                    try:
                        evaluated = _safe_eval(entry.value)
                    except ValueError:
                        continue
                    if isinstance(evaluated, str):
                        icon = evaluated
                if target.id in {"CATEGORIES", "__categories__"}:
                    try:
                        evaluated_categories = _safe_eval(entry.value)
                    except ValueError:
                        continue
                    categories = [str(cat) for cat in _as_sequence(evaluated_categories)]
    return icon, tuple(categories)


def _build_metadata(
    node: ast.AST,
    decorator: ast.Call,
    path: Path,
    qualified: tuple[str, tuple[str, ...]],
    module_icon: str | None,
    module_categories: tuple[str, ...],
    file_hash: str,
) -> ScannedScript:
    name = _decorator_name(decorator.func)
    if name is None:
        raise ValueError("Unsupported decorator")

    kwargs = _collect_kwargs(decorator)

    if name == "service":
        identifier = _require_str(kwargs.get("service_id"), "service_id")
    else:
        identifier = _require_str(kwargs.get("script_id"), "script_id")
    
    title = _require_str(kwargs.get("title"), "title")
    description = _require_str(kwargs.get("description"), "description")
    timeout = _optional_float(kwargs.get("timeout"))

    if name == "service_script":
        related_service = _require_str(kwargs.get("service_id"), "service_id")
    else:
        related_service = None

    accepts_value = kwargs.get("accepts")
    accepts = tuple(str(item) for item in _as_sequence(accepts_value))

    module_name, group = qualified
    callable_name = getattr(node, "name", "<unknown>")
    qualname = f"{module_name}:{callable_name}"
    docstring = ast.get_docstring(node)

    parameters = _collect_parameter_names(node)

    icon_value = kwargs.get("icon")
    icon = icon_value if isinstance(icon_value, str) else None
    if icon is None:
        icon = module_icon

    categories_value = kwargs.get("categories")
    if categories_value is not None:
        categories = tuple(str(item) for item in _as_sequence(categories_value))
    else:
        categories = module_categories

    return ScannedScript(
        identifier=identifier,
        kind=name,
        title=title,
        description=description,
        docstring=docstring,
        file_path=path,
        module=module_name,
        qualname=qualname,
        group=tuple(group),
        accepts=accepts,
        timeout=timeout,
        related_service_id=related_service,
        icon=icon,
        categories=categories,
        file_hash=file_hash,
        parameters=parameters,
    )


def _collect_kwargs(call: ast.Call) -> dict[str, object]:
    data: dict[str, object] = {}
    for keyword in call.keywords:
        if keyword.arg is None:
            continue
        try:
            value = _safe_eval(keyword.value)
        except ValueError:
            data[keyword.arg] = None
        else:
            data[keyword.arg] = value
    return data


def _safe_eval(node: ast.AST) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return tuple(_safe_eval(elem) for elem in node.elts)
    if isinstance(node, ast.Dict):
        keys = []
        values = []
        for key, value in zip(node.keys, node.values):
            keys.append(_safe_eval(key))
            values.append(_safe_eval(value))
        return {k: v for k, v in zip(keys, values)}
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_attr_chain(node)}"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _safe_eval(node.operand)
        if isinstance(value, (int, float)):
            return -value
    raise ValueError("Unsupported expression in decorator")


def _attr_chain(node: ast.Attribute) -> str:
    pieces: list[str] = []
    current: ast.AST | None = node
    while isinstance(current, ast.Attribute):
        pieces.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        pieces.append(current.id)
    pieces.reverse()
    return ".".join(pieces)


def _require_str(value: object | None, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Decorator field '{field}' must be a string literal")
    return value


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError("timeout must be a number")


def _as_sequence(value: object | None) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, (tuple, list, set)):
        return tuple(value)
    return (value,)


def _collect_parameter_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = node.args
        names: list[str] = [arg.arg for arg in args.args]
        if args.vararg is not None:
            names.append("*" + args.vararg.arg)
        names.extend(kwonly.arg for kwonly in args.kwonlyargs)
        if args.kwarg is not None:
            names.append("**" + args.kwarg.arg)
        return tuple(names)
    return tuple()
