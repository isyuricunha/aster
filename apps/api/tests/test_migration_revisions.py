from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_ids_fit_the_version_table() -> None:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    revisions = list(script.walk_revisions())
    assert revisions
    assert all(len(revision.revision) <= 32 for revision in revisions)
