from __future__ import annotations

from app.config_backup.diff import diff_configs


def test_diff_configs() -> None:
    before = "interface Gi0/0\n description old\n"
    after = "interface Gi0/0\n description new\n"
    diff = diff_configs(before, after, "old", "new")
    assert "- description old" in diff
    assert "+ description new" in diff
