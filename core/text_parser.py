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


def _is_trade_line(line: str) -> bool:
    """判断是否为真实的交易行（而非UI文字）
    真实交易行格式：
      组合: "5  FC  6-12  10  95  700  吃"  (至少5个token，末尾含独立"吃")
      单号: "3  3  5  5  92  110/30  吃"    (至少5个token，末尾含独立"吃")
    排除：
      "吃(x$)", "全吃", "吃 预测彩", "预测彩吃票等待" 等UI文字
    """
    line = line.strip()
    if not line:
        return False
    # "吃" 必须作为独立 token 出现（不能是 "全吃"、"吃(x$)"、"吃 预测彩" 等）
    tokens = line.split()
    has_eat = False
    for t in tokens:
        if t == "吃":
            has_eat = True
            break
    if not has_eat:
        return False
    # 至少5个token才像交易记录行
    if len(tokens) < 5:
        return False
    return True


def _parse_trades(text: str) -> list[TradeRow]:
    """
    仅提取「我的交易」→「已证实交易」区域的数据。
      组合: "5  FC  6-12  10  95  700  吃"  → horse_combo="6-12"
      单号: "3  3  5  5  92  110/30  吃"  → horse_combo="3"
    """
    race_num = _extract_race_num(text)
    seen = set()
    trades = []

    def _add(combo):
        if combo and combo not in seen:
            seen.add(combo)
            trades.append(TradeRow(horse_combo=combo, race=race_num))

    # 策略1: 从「已证实交易」区域提取
    section = _find_confirmed_section(text)
    if section:
        print(f"[解析] 已证实区域长度={len(section)}, 内容前200字: {section[:200]}")
        _extract_from_section(section, _add)
        if trades:
            return trades

    # 策略2: 没有「已证实」标题时，在「我的交易」和「未证实」之间找含独立"吃"的交易行
    my_trade_idx = text.find("我的交易")
    if my_trade_idx == -1:
        return []

    rest = text[my_trade_idx:]
    # 截断到「未证实」之前
    unconfirmed_idx = rest.find("未证实")
    if unconfirmed_idx != -1:
        rest = rest[:unconfirmed_idx]

    # 只提取真实交易行
    trade_lines = [l for l in rest.split("\n") if _is_trade_line(l)]
    if not trade_lines:
        return []

    print(f"[解析] 策略2: 找到{len(trade_lines)}条交易行")
    for tl in trade_lines[:5]:
        print(f"  {tl}")

    combined_lines = "\n".join(trade_lines)
    has_combos = bool(re.search(r'(?<!\d)\d{1,2}-\d{1,2}(?!\d)', combined_lines))

    for line in trade_lines:
        if has_combos:
            _extract_combos_only(line, _add)
        else:
            _extract_from_line(line, _add)

    return trades


def _find_confirmed_section(text: str) -> str | None:
    """在「我的交易」范围内找「已证实交易」区域"""
    # 必须先找到「我的交易」
    my_trade_idx = text.find("我的交易")
    if my_trade_idx == -1:
        return None

    # 只在「我的交易」之后的文本中搜索
    search_text = text[my_trade_idx:]

    # 严格匹配「已证实交易」或「已证实」（必须有"已"）
    confirmed_start = -1
    for m in re.finditer(r'已证实交易|已证实', search_text):
        start = m.start()
        # 排除「未已证实」（虽然不太可能）
        if start > 0 and search_text[start - 1] == '未':
            continue
        confirmed_start = m.end()
        break

    if confirmed_start == -1:
        return None

    rest = search_text[confirmed_start:]

    # 截断到「未证实交易」或其他边界
    boundaries = ["未证实", "S-TAB"]
    end_pos = len(rest)
    for b in boundaries:
        idx = rest.find(b)
        if idx != -1 and idx < end_pos:
            end_pos = idx

    return rest[:end_pos]


def _extract_from_section(section: str, add_fn):
    """从已证实区域文本中提取所有马号（组合+单号）
    如果整个区域存在 X-Y 组合格式，则只提取组合，不提取单号
    """
    # 只处理真实交易行
    trade_lines = [l for l in section.split("\n") if _is_trade_line(l)]
    if not trade_lines:
        return

    combined = "\n".join(trade_lines)
    has_combos = bool(re.search(r'(?<!\d)\d{1,2}-\d{1,2}(?!\d)', combined))

    for line in trade_lines:
        if has_combos:
            _extract_combos_only(line, add_fn)
        else:
            _extract_from_line(line, add_fn)


def _extract_combos_only(line: str, add_fn):
    """仅提取 X-Y 组合格式，忽略单号"""
    combos = re.findall(r'(?<!\d)(\d{1,2}-\d{1,2})(?!\d)', line)
    for c in combos:
        add_fn(c)


def _extract_from_line(line: str, add_fn):
    """从单行交易记录中提取马号（仅在无组合时用于提取单号）"""
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
