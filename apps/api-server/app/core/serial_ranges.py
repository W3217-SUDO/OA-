"""新系统自编号的号段。

旧沪知系统仍在用，按“最大号+1”取号，并持续同步进新系统；新系统自己编号时只在本号段内取最大号+1，
旧编号（号段以下）归旧系统，两边不再撞号。
"""

NEW_SYSTEM_SERIAL_START = {"customer": 50001, "contract": 50001, "case": 50001, "clue": 8001}


def next_in_range(sequences, module: str) -> int:
    start = NEW_SYSTEM_SERIAL_START[module]
    return max((value for value in sequences if value >= start), default=start - 1) + 1
