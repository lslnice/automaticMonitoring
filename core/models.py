"""数据模型定义"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TradeRow:
    """一条已证实交易"""
    horse_combo: str = ""    # 马号 "1-2"
    race: str = ""           # 场次 "2"
    cells: tuple = ()        # 原始单元格文本（用于表格显示）


@dataclass(frozen=True)
class HeaderData:
    """页面头部信息"""
    account_name: str = ""       # bb6633
    credit_balance: str = ""     # HK$975,285.42
    race_location: str = ""      # 纽卡斯尔
    race_number: str = ""        # 2


@dataclass(frozen=True)
class PageSnapshot:
    """页面快照"""
    header: HeaderData
    trades: tuple          # tuple[TradeRow, ...]
    page_index: int = 0
    timestamp: float = 0.0
