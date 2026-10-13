import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "src" / "infra" / "prisma" / "migrations"
NAMED_MIGRATION = re.compile(r"^\d{14}_[a-z0-9]+(?:_[a-z0-9]+)*$")
# Aplicada antes da regra existir; não pode ser renomeada sem quebrar o histórico do Prisma.
LEGACY_UNNAMED = frozenset({"20260526213743_"})


def test_every_migration_folder_has_descriptive_name() -> None:
    folders = [entry.name for entry in MIGRATIONS_DIR.iterdir() if entry.is_dir()]

    unnamed = [
        name for name in folders if name not in LEGACY_UNNAMED and not NAMED_MIGRATION.match(name)
    ]

    assert folders
    assert unnamed == []
