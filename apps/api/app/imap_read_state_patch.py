from dataclasses import replace

from app import communication_adapters

_installed = False


def install_imap_read_state_patch() -> None:
    global _installed
    if _installed:
        return

    original = communication_adapters._parse_imap_message

    def parse_imap_message(
        raw: bytes,
        *,
        uid: str,
        folder: str,
        flags: str,
    ) -> communication_adapters.ReceivedMessage:
        message = original(
            raw,
            uid=uid,
            folder=folder,
            flags=flags,
        )
        is_read = "\\seen" in flags.casefold()
        if message.is_read == is_read:
            return message
        return replace(message, is_read=is_read)

    communication_adapters._parse_imap_message = parse_imap_message
    _installed = True
