from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.prompt_library import CHAT_SYSTEM_PROMPT, render_persona


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


def compose_persona_messages(persona: PersonaConfiguration) -> list[CanonicalMessage]:
    messages = [
        CanonicalMessage(
            role=MessageRole.SYSTEM,
            source=MessageSource.PLATFORM,
            content=CHAT_SYSTEM_PROMPT,
        )
    ]
    persona_content = render_persona(persona.name, persona.instructions)
    if persona.enabled and persona_content:
        messages.append(
            CanonicalMessage(
                role=persona.instruction_role,
                source=MessageSource.PERSONA,
                content=persona_content,
            )
        )
    return messages


def compose_messages(
    *,
    persona: PersonaConfiguration,
    history: Sequence[CanonicalMessage] = (),
    current_user_message: str,
) -> list[CanonicalMessage]:
    messages = compose_persona_messages(persona)
    messages.extend(history)
    messages.append(
        CanonicalMessage(
            role=MessageRole.USER,
            source=MessageSource.USER,
            content=current_user_message,
        )
    )
    return messages
