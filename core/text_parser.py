"""
纯文本解析：从页面 innerText 中提取「已证实交易」的马号
支持组合 (1-2) 和单号 (3)
"""
import re
from core.models import HeaderData, TradeRow


def parse_page_text(text: str) -> dict:
    header = _parse_header(text)
    trades = _parse_trades(text)
    return {"header": header, "trades": trades}


def _parse_header(text: str) -> HeaderData:
    account = ""
    balance = ""
    location = ""
    race_num = ""

    m = re.search(r'([a-zA-Z]\w{3,10})\s+信用余额\s*(HK\$[\d,]+\.?\d*)', text)
    if m:
        account = m.group(1)
        balance = m.group(2)

    locations = [
        "纽卡斯尔", "提阿洛亚", "沙田", "跑马地", "快活谷",
        "伊普威治", "启莫", "多宝", "达尔文", "墨尔本",
        "沃格", "枫丹白露", "Newcastle", "Te Aroha", "Kilmore",
        "Wagga", "Fontainebleau",
    ]
    for loc in locations:
        if loc in text:
            location = loc
            break

    m = re.search(r'场\s*(\d+)', text)
    if m:
        race_num = m.group(1)

    return HeaderData(
        account_name=account,
        credit_balance=balance,
        race_location=location,
        race_number=race_num,
    )


def _parse_trades(text: str) -> list[TradeRow]:
    """
    提取已证实交易。支持两种格式：
      组合: "8  2-6  10  85  700  吃"  → horse_combo="2-6"
      单号: "3  3  5  5  92  110/30  吃"  → horse_combo="3"
    """
    race_num = _extract_race_num(text)
    seen = set()
    trades = []

    def _add(combo):
        if combo and combo not in seen:
            seen.add(combo)
            trades.append(TradeRow(horse_combo=combo, race=race_num))

    # ---------- 策略1: "已证实" 区域 ----------
    section = _find_confirmed_section(text)
    if section:
        _extract_from_section(section, _add)
        if trades:
            return trades

    # ---------- 策略2: 含 "吃" 的行 ----------
    trade_idx = text.find("我的交易")
    if trade_idx == -1:
        return []

    rest = text[trade_idx:]
    # 截断到"未证实"之前
    for boundary in ["未证实", "S-TAB", "贴士", "仅供参考"]:
        bi = rest.find(boundary, 10)
        if bi != -1:
            rest = rest[:bi]

    for line in rest.split("\n"):
        if "吃" not in line:
            continue
        _extract_from_line(line, _add)

    return trades


def _find_confirmed_section(text: str) -> str | None:
    """找到"已证实"区域文本，返回该区域；找不到返回 None"""
    confirmed_start = -1
    for m in re.finditer(r'(?<!未)已?证实交?易?', text):
        start = m.start()
        prefix = text[max(0, start - 1):start]
        if prefix != "未":
            confirmed_start = m.end()
            break

    if confirmed_start == -1:
        return None

    rest = text[confirmed_start:]
    boundaries = ["未证实", "S-TAB", "贴士", "赛事", "彩池", "预测彩",
                   "仅供参考", "即将开始", "我的喜爱", "星期"]
    end_pos = len(rest)
    for b in boundaries:
        idx = rest.find(b)
        if idx != -1 and idx < end_pos:
            end_pos = idx

    return rest[:end_pos]


def _extract_from_section(section: str, add_fn):
    """从已证实区域文本中提取所有马号（组合+单号）"""
    for line in section.split("\n"):
        _extract_from_line(line, add_fn)


def _extract_from_line(line: str, add_fn):
    """从单行文本中提取马号"""
    # 1) 组合: X-Y 格式
    combos = re.findall(r'(?<!\d)(\d{1,2}-\d{1,2})(?!\d)', line)
    if combos:
        for c in combos:
            add_fn(c)
        return

    # 2) 单号: 行内无组合，按空白拆分，第二个小数字为马号
    #    格式: "3  3  5  5  92  110/30  吃"
    #           场  马  独赢 位置 %   限额   状态
    tokens = line.split()
    # 找所有 1~20 的纯数字 token
    small_nums = []
    for t in tokens:
        if re.match(r'^\d{1,2}$', t):
            num = int(t)
            if 1 <= num <= 20:
                small_nums.append(t)

    # 至少要有 2 个小数字（场次 + 马号），取第二个
    if len(small_nums) >= 2:
        horse = small_nums[1]
        add_fn(horse)


def _extract_race_num(text: str) -> str:
    m = re.search(r'场\s*(\d+)', text)
    return m.group(1) if m else ""
