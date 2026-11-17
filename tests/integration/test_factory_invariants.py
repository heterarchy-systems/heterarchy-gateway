"""Check factory invariants absent from the supplied source guard implementation."""

import ast
from pathlib import Path

from guardrails.source_guardrails import WideTypeGuard


def test_factory_dtos_remain_required_immutable_and_avoid_frozen_sets() -> None:
    source_root = Path(__file__).resolve().parents[2] / "app"
    violations: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "frozenset":
                    violations.append(f"{path}:{node.lineno} uses frozenset")
            if not isinstance(node, ast.ClassDef):
                continue
            for decorator in node.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "dataclass"
                ):
                    continue
                required_flags = {"frozen", "slots", "kw_only"}
                enabled_flags = {
                    keyword.arg
                    for keyword in decorator.keywords
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                }
                if not required_flags.issubset(enabled_flags):
                    violations.append(f"{path}:{node.lineno} requires immutable DTO flags")
                for field in node.body:
                    if isinstance(field, ast.AnnAssign) and field.value is not None:
                        violations.append(f"{path}:{field.lineno} defines a DTO field default")
    assert not violations, "\n".join(violations)


def test_test_sources_preserve_the_same_narrow_type_boundary() -> None:
    test_root = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    for path in sorted(test_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        guard = WideTypeGuard(source, str(path))
        guard.visit(ast.parse(source))
        violations.extend(
            f"{violation.path}:{violation.line} {violation.message}"
            for violation in guard.violations
        )
    assert not violations, "\n".join(violations)
