from collections.abc import Sequence
from typing import Literal

InstructionRole = Literal["system", "developer"]


def normalize_provider_messages(
    *,
    instruction_role: InstructionRole,
    messages: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for message in messages:
        item = dict(message)
        if item.get("role") in {"system", "developer"}:
            item["role"] = instruction_role
        normalized.append(item)
    return normalized
