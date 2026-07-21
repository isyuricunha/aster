from app.imap_read_state_patch import install_imap_read_state_patch
from app.imap_sync_patch import install_imap_sync_patch

_installed = False


def install_communication_runtime() -> None:
    global _installed
    if _installed:
        return
    install_imap_read_state_patch()
    install_imap_sync_patch()
    _installed = True
