from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class MessageRole(StrEnum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageSource(StrEnum):
    PLATFORM = "platform"
    PERSONA = "persona"
    CONVERSATION = "conversation"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class CanonicalMessage:
    role: MessageRole
    source: MessageSource
    content: str


@dataclass(frozen=True, slots=True)
class PersonaConfiguration:
    name: str
    instructions: str
    enabled: bool
    instruction_role: MessageRole


def _render_persona(persona: PersonaConfiguration) -> str:
    parts: list[str] = []
    if persona.name:
        parts.append(f"Your name is {persona.name}.")
    if persona.instructions.strip():
        parts.append(persona.instructions)
    return "\n\n".join(parts)


def compose_messages(
    *,
    persona: PersonaConfiguration,
    history: Sequence[CanonicalMessage] = (),
    current_user_message: str,
) -> list[CanonicalMessage]:
    messages: list[CanonicalMessage] = []
    persona_content = _render_persona(persona)

    if persona.enabled and persona_content:
        if persona.instruction_role is MessageRole.SYSTEM:
            persona_content = (
                "[USER_DEFINED_PERSONA]\n"
                f"{persona_content}\n"
                "[/USER_DEFINED_PERSONA]"
            )
        messages.append(
            CanonicalMessage(
                role=persona.instruction_role,
                source=MessageSource.PERSONA,
                content=persona_content,
            )
        )

    messages.extend(history)
    messages.append(
        CanonicalMessage(
            role=MessageRole.USER,
            source=MessageSource.USER,
            content=current_user_message,
        )
    )
    return messages
