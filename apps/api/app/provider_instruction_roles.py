from collections.abc import Sequence
from typing import Literal

InstructionRole = Literal["system", "developer"]

_roles: dict[tuple[str, str], InstructionRole] = {}


def register_provider_instruction_role(
    *,
    base_url: str,
    model_id: str,
    instruction_role: InstructionRole,
) -> None:
    _roles[(base_url, model_id)] = instruction_role


def provider_instruction_role(*, base_url: str, model_id: str) -> InstructionRole:
    return _roles.get((base_url, model_id), "system")


def normalize_provider_messages(
    *,
    base_url: str,
    model_id: str,
    messages: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    instruction_role = provider_instruction_role(base_url=base_url, model_id=model_id)
    normalized: list[dict[str, object]] = []
    for message in messages:
        item = dict(message)
        if item.get("role") in {"system", "developer"}:
            item["role"] = instruction_role
        normalized.append(item)
    return normalized


def clear_provider_instruction_roles() -> None:
    _roles.clear()
