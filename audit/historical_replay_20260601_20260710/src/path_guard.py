from __future__ import annotations

from pathlib import Path


class PathGuardError(ValueError):
    pass


def _resolved_existing_parent(path: Path) -> Path:
    current = path
    missing: list[str] = []
    while not current.exists():
        missing.append(current.name)
        parent = current.parent
        if parent == current:
            raise PathGuardError(f"cannot resolve parent for {path}")
        current = parent
    resolved = current.resolve(strict=True)
    for name in reversed(missing):
        resolved = resolved / name
    return resolved


def assert_safe_output(root: Path, target: Path) -> Path:
    root_resolved = root.resolve(strict=False)
    target_abs = target if target.is_absolute() else root_resolved / target
    target_resolved = _resolved_existing_parent(target_abs)

    try:
        target_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PathGuardError(f"output escapes audit root: {target_resolved}") from exc

    current = target_abs
    while current != root_resolved:
        if current.exists() and current.is_symlink():
            raise PathGuardError(f"symlink component rejected: {current}")
        parent = current.parent
        if parent == current:
            raise PathGuardError(f"cannot reach audit root from target: {target_abs}")
        current = parent

    return target_resolved


def ensure_within_root(root: Path, target: Path) -> Path:
    """Return a path proven to remain inside the audit output root."""
    return assert_safe_output(root, target)
