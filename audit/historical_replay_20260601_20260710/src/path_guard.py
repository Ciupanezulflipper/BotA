from __future__ import annotations

from pathlib import Path


class PathGuardError(RuntimeError):
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
    root_resolved = root.resolve(strict=True)
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
        current = current.parent

    return target_resolved


def ensure_within_root(root: Path, target: Path) -> Path:
    """Compatibility entry point for sidecar modules.

    All callers receive the same containment and symlink protections implemented
    by ``assert_safe_output``. Keeping one implementation avoids drift between
    read-verification and write-path guards.
    """
    return assert_safe_output(root, target)
