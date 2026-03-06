"""
已证实交易归类逻辑
组合: 1-2, 1-3, 1-4, 3-6, 6-4, 6-9  →  1-2.3.4, 6-3.4.9
单号: 3, 5                           →  3.5
"""
from collections import Counter


def group_trades(combos: list[str]) -> list[str]:
    """
    将交易号码列表归类分组。支持组合(X-Y)和单号(X)。

    Args:
        combos: ["1-2", "1-3", "3", "5"]

    Returns:
        ["1-2.3", "3.5"]  (组合归类在前，单号在后)
    """
    if not combos:
        return []

    pairs = []       # 组合
    singles = []     # 单号
    seen_pairs = set()
    seen_singles = set()

    for combo in combos:
        combo = combo.strip()
        if "-" in combo:
            parts = combo.split("-", 1)
            try:
                a, b = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            key = (a, b)
            if key not in seen_pairs:
                seen_pairs.add(key)
                pairs.append((a, b))
        else:
            try:
                n = int(combo)
            except ValueError:
                continue
            if n not in seen_singles:
                seen_singles.add(n)
                singles.append(n)

    result = []

    # ---- 组合归类 ----
    if pairs:
        result.extend(_group_pairs(pairs))

    # ---- 单号：每个独立一行 ----
    for s in sorted(singles):
        result.append(str(s))

    return result


def _group_pairs(pairs: list[tuple[int, int]]) -> list[str]:
    """组合归类：按出现频率最高的号码作为 key 分组"""
    freq = Counter()
    for a, b in pairs:
        freq[a] += 1
        freq[b] += 1

    groups = {}
    for a, b in pairs:
        if freq[a] >= freq[b]:
            key_num, partner = a, b
        else:
            key_num, partner = b, a
        if freq[a] == freq[b]:
            key_num, partner = a, b

        if key_num not in groups:
            groups[key_num] = []
        if partner not in groups[key_num]:
            groups[key_num].append(partner)

    result = []
    for key_num in sorted(groups.keys()):
        partners = sorted(groups[key_num])
        partners_str = ".".join(str(p) for p in partners)
        result.append(f"{key_num}-{partners_str}")

    return result


def format_message(grouped: list[str], suffix: str, amount: str) -> str:
    lines = []
    for g in grouped:
        line = g
        if suffix:
            line += suffix
        if amount:
            line += amount
        lines.append(line)
    return "\n".join(lines)
