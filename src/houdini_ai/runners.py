from __future__ import annotations

import types
from collections.abc import Callable, Mapping, Sequence
from dataclasses import fields, is_dataclass
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

from .costs import ApprovalRequired, CostGate, CostTier


ParamsT = TypeVar("ParamsT")
ResultT = TypeVar("ResultT")
_FORBIDDEN_COMMAND_FIELDS = {"argv", "command", "commands"}


def _matches_type(value: Any, annotation: Any) -> bool:
    if annotation is Any:
        return True
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin in (Union, types.UnionType):
        return any(_matches_type(value, option) for option in arguments)
    if origin is not None:
        if origin in (list, Sequence):
            return isinstance(value, list) and all(_matches_type(item, arguments[0]) for item in value)
        if origin in (dict, Mapping):
            return isinstance(value, Mapping) and all(
                _matches_type(key, arguments[0]) and _matches_type(item, arguments[1])
                for key, item in value.items()
            )
        if origin is tuple:
            if not isinstance(value, tuple):
                return False
            if len(arguments) == 2 and arguments[1] is Ellipsis:
                return all(_matches_type(item, arguments[0]) for item in value)
            return len(value) == len(arguments) and all(_matches_type(item, expected) for item, expected in zip(value, arguments))
    if annotation is None or annotation is type(None):
        return value is None
    return isinstance(value, annotation)


def _contains_command_array(value: Mapping[str, Any]) -> bool:
    for key, item in value.items():
        if key.lower() in _FORBIDDEN_COMMAND_FIELDS and isinstance(item, (list, tuple)):
            return True
        if isinstance(item, Mapping) and _contains_command_array(item):
            return True
    return False


class RunnerRegistry:
    """Allowlist dispatcher that constructs validated typed parameter objects."""

    def __init__(self) -> None:
        self._runners: dict[str, tuple[type[Any], Callable[[Any], Any], CostTier]] = {}

    def register(
        self,
        runner_id: str,
        params_type: type[ParamsT],
        runner: Callable[[ParamsT], ResultT],
        *,
        cost_tier: CostTier | str = CostTier.PROBE,
    ) -> None:
        if not runner_id:
            raise ValueError("runner_id must not be empty")
        if runner_id in self._runners:
            raise ValueError(f"runner already registered: {runner_id}")
        if not isinstance(params_type, type) or not is_dataclass(params_type):
            raise TypeError("params_type must be a dataclass type")
        self._runners[runner_id] = (params_type, runner, CostTier(cost_tier))

    @property
    def registered_ids(self) -> tuple[str, ...]:
        return tuple(self._runners)

    def dispatch(
        self,
        runner_id: str,
        params: Mapping[str, Any],
        *,
        approval: Mapping[str, Any] | None = None,
    ) -> Any:
        try:
            params_type, runner, cost_tier = self._runners[runner_id]
        except KeyError:
            raise KeyError(f"unregistered runner: {runner_id}") from None
        if not isinstance(params, Mapping):
            raise TypeError("runner params must be a mapping")
        if _contains_command_array(params):
            raise TypeError("command arrays are not accepted as runner params")
        approved = (
            isinstance(approval, Mapping)
            and approval.get("approved") is True
            and approval.get("runner_id") == runner_id
            and approval.get("cost_tier") == cost_tier.value
        )
        try:
            CostGate().require(cost_tier, approved=approved)
        except ApprovalRequired:
            raise

        expected_fields = {field.name: field for field in fields(params_type)}
        extras = set(params) - set(expected_fields)
        if extras:
            raise TypeError(f"unexpected runner params: {', '.join(sorted(extras))}")
        hints = get_type_hints(params_type)
        for name, value in params.items():
            annotation = hints.get(name, expected_fields[name].type)
            if not _matches_type(value, annotation):
                raise TypeError(f"invalid type for runner param {name}")
        try:
            typed_params = params_type(**dict(params))
        except TypeError as exc:
            raise TypeError(f"invalid runner params: {exc}") from exc
        return runner(typed_params)
