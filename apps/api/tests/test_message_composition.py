from app.message_composition import (
    CanonicalMessage,
    MessageRole,
    MessageSource,
    PersonaConfiguration,
    compose_messages,
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
        CanonicalMessage(
            role=MessageRole.USER,
            source=MessageSource.USER,
            content=user_message,
        )
    ]


def test_developer_persona_is_separate_from_user_message() -> None:
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
        MessageRole.DEVELOPER,
        MessageRole.USER,
    ]
    assert messages[0].source is MessageSource.PERSONA
    assert messages[0].content == (
        "Your name is Aster.\n\n"
        "Answer in the user's language.\nKeep the tone natural."
    )
    assert messages[1].content == "Explique volumes Docker."


def test_system_persona_is_delimited() -> None:
    messages = compose_messages(
        persona=PersonaConfiguration(
            name="",
            instructions="Use concise answers.",
            enabled=True,
            instruction_role=MessageRole.SYSTEM,
        ),
        current_user_message="Hello",
    )

    assert messages[0] == CanonicalMessage(
        role=MessageRole.SYSTEM,
        source=MessageSource.PERSONA,
        content=(
            "[USER_DEFINED_PERSONA]\n"
            "Use concise answers.\n"
            "[/USER_DEFINED_PERSONA]"
        ),
    )


def test_empty_persona_does_not_create_an_instruction_message() -> None:
    messages = compose_messages(
        persona=PersonaConfiguration(
            name="",
            instructions="   ",
            enabled=True,
            instruction_role=MessageRole.DEVELOPER,
        ),
        current_user_message="Hello",
    )

    assert len(messages) == 1
    assert messages[0].role is MessageRole.USER


def test_history_keeps_its_order_and_source() -> None:
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

    assert messages[:2] == history
    assert messages[-1].content == "Current question"
