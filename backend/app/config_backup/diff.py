from __future__ import annotations

import difflib


def diff_configs(old: str, new: str, from_label: str = "old", to_label: str = "new") -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, from_label, to_label)
    return "".join(diff)
