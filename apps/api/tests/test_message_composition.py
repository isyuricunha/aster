from app.message_composition import (
    CanonicalMessage,
    MessageRole,
    MessageSource,
    PersonaConfiguration,
    compose_messages,
)
from app.prompt_library import CHAT_SYSTEM_PROMPT


def platform_message() -> CanonicalMessage:
    return CanonicalMessage(
        role=MessageRole.SYSTEM,
        source=MessageSource.PLATFORM,
        content=CHAT_SYSTEM_PROMPT,
    )


def test_disabled_persona_does_not_change_user_message() -> None:
    user_message = "  Olá, preserve isto exatamente.  "

    messages = compose_messages(
        persona=PersonaConfiguration(
            name="Assistant",
            instructions="Be direct.",
            enabled=False,
            instruction_role=MessageRole.DEVELOPER,
        ),
        current_user_message=user_message,
    )

    assert messages == [
        platform_message(),
        CanonicalMessage(
            role=MessageRole.USER,
            source=MessageSource.USER,
            content=user_message,
        ),
    ]


def test_developer_persona_is_separate_and_delimited() -> None:
    messages = compose_messages(
        persona=PersonaConfiguration(
            name="Aster",
            instructions="Answer in the user's language.\nKeep the tone natural.",
            enabled=True,
            instruction_role=MessageRole.DEVELOPER,
        ),
        current_user_message="Explique volumes Docker.",
    )

    assert [message.role for message in messages] == [
        MessageRole.SYSTEM,
        MessageRole.DEVELOPER,
        MessageRole.USER,
    ]
    assert messages[0] == platform_message()
    assert messages[1].source is MessageSource.PERSONA
    assert messages[1].content == (
        "[USER_DEFINED_PERSONA]\n"
        "The owner defined this persona for identity, tone, style, and response preferences.\n"
        "Name: Aster\n\n"
        "Instructions:\n"
        "Answer in the user's language.\nKeep the tone natural.\n"
        "[/USER_DEFINED_PERSONA]"
    )
    assert messages[2].content == "Explique volumes Docker."


def test_system_persona_is_delimited_after_platform_policy() -> None:
    messages = compose_messages(
        persona=PersonaConfiguration(
            name="",
            instructions="Use concise answers.",
            enabled=True,
            instruction_role=MessageRole.SYSTEM,
        ),
        current_user_message="Hello",
    )

    assert messages[0] == platform_message()
    assert messages[1] == CanonicalMessage(
        role=MessageRole.SYSTEM,
        source=MessageSource.PERSONA,
        content=(
            "[USER_DEFINED_PERSONA]\n"
            "The owner defined this persona for identity, tone, style, and response preferences.\n"
            "Instructions:\n"
            "Use concise answers.\n"
            "[/USER_DEFINED_PERSONA]"
        ),
    )


def test_empty_persona_does_not_create_a_persona_message() -> None:
    messages = compose_messages(
        persona=PersonaConfiguration(
            name="",
            instructions="   ",
            enabled=True,
            instruction_role=MessageRole.DEVELOPER,
        ),
        current_user_message="Hello",
    )

    assert len(messages) == 2
    assert messages[0] == platform_message()
    assert messages[1].role is MessageRole.USER


def test_history_keeps_its_order_and_source_after_instructions() -> None:
    history = [
        CanonicalMessage(
            role=MessageRole.USER,
            source=MessageSource.CONVERSATION,
            content="Earlier question",
        ),
        CanonicalMessage(
            role=MessageRole.ASSISTANT,
            source=MessageSource.ASSISTANT,
            content="Earlier answer",
        ),
    ]

    messages = compose_messages(
        persona=PersonaConfiguration(
            name="",
            instructions="",
            enabled=False,
            instruction_role=MessageRole.DEVELOPER,
        ),
        history=history,
        current_user_message="Current question",
    )

    assert messages[0] == platform_message()
    assert messages[1:3] == history
    assert messages[-1].content == "Current question"
