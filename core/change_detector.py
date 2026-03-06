"""新旧快照对比"""
from dataclasses import fields
from core.models import PageSnapshot, HeaderData


def detect_changes(old: PageSnapshot, new: PageSnapshot) -> dict | None:
    if old == new:
        return None

    changes = {}

    # Header 变化
    header_changes = {}
    for f in fields(HeaderData):
        if getattr(old.header, f.name) != getattr(new.header, f.name):
            header_changes[f.name] = True
    if header_changes:
        changes["header"] = header_changes

    # Trades 变化（只比较马号集合）
    old_combos = {t.horse_combo for t in old.trades}
    new_combos = {t.horse_combo for t in new.trades}
    if old_combos != new_combos:
        changes["trades"] = {
            "added": list(new_combos - old_combos),
            "removed": list(old_combos - new_combos),
        }

    return changes if changes else None
