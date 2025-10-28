from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from functools import wraps


class ToolFunction:
    """Simple wrapper that carries metadata for a Python function tool."""

    def __init__(self, fn: Callable[..., Any], name: Optional[str] = None, description: Optional[str] = None):
        self.fn = fn
        self.name = name or fn.__name__
        self.description = description or (fn.__doc__ or "")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.fn(*args, **kwargs)

    def spec(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description}


def tool(fn: Callable[..., Any] | None = None, *, name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to mark a function as a tool.

    Usage:
        @tool
        def do(x: str) -> str: ...
    """

    def _wrap(func: Callable[..., Any]) -> ToolFunction:
        wrapped = ToolFunction(func, name=name, description=description)
        @wraps(func)
        def inner(*args: Any, **kwargs: Any) -> Any:
            return wrapped(*args, **kwargs)
        inner._af_tool = wrapped  # type: ignore[attr-defined]
        return inner  # type: ignore[return-value]

    return _wrap if fn is None else _wrap(fn)


