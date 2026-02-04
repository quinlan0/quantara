#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时监控数据的SQLite存储模块

- 使用单独的类封装SQLite读写逻辑
- 数据库文件路径由外部显式传入（与pkl同目录）
"""

import sqlite3
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional, Union
from datetime import datetime


class RealTimeMonitorSQLite:
    """
    实时监控数据的SQLite存储类

    设计要点：
    - 不保存股票名称，只保存股票代码和数值字段
    - 每一次监控、每一个股票一行数据
    - 为 (code, ts) 建立联合索引，便于按股票和时间查询
    """

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self._ensure_dir()
        self._init_db()

    # -------------------- 基础结构 -------------------- #
    def _ensure_dir(self) -> None:
        """确保数据库所在目录存在"""
        if self.db_path.parent and not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        """获取SQLite连接"""
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """初始化数据库结构"""
        with self._get_conn() as conn:
            cur = conn.cursor()
            # 统一字段命名为英文，语义映射自real_time_monitor中的指标字段
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS real_time_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    current_price REAL,       -- 当前价格
                    high_price REAL,          -- 当日最高价
                    low_price REAL,           -- 当日最低价
                    current_change REAL,      -- 当前涨跌幅
                    volume_ratio REAL,        -- 量比
                    prev_5_change REAL,       -- 前五日涨跌幅
                    prev_day_change REAL,     -- 上一日涨跌幅
                    open_change REAL,         -- 当日开盘涨跌幅
                    high_change REAL,         -- 当日最高涨跌幅
                    low_change REAL,          -- 当日最低涨跌幅
                    current_volume INTEGER,   -- 当日成交量
                    prev_5_volumes INTEGER    -- 前五日平均量
                )
                """
            )
            # 联合索引：code + ts
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_real_time_indicators_code_ts
                ON real_time_indicators(code, ts)
                """
            )

            # 兼容已有数据库：如果旧表中缺少价格相关列，则动态添加
            cur.execute("PRAGMA table_info(real_time_indicators)")
            existing_cols = {row[1] for row in cur.fetchall()}
            alter_stmts = []
            if "current_price" not in existing_cols:
                alter_stmts.append("ALTER TABLE real_time_indicators ADD COLUMN current_price REAL")
            if "high_price" not in existing_cols:
                alter_stmts.append("ALTER TABLE real_time_indicators ADD COLUMN high_price REAL")
            if "low_price" not in existing_cols:
                alter_stmts.append("ALTER TABLE real_time_indicators ADD COLUMN low_price REAL")

            for stmt in alter_stmts:
                cur.execute(stmt)

            conn.commit()

    # -------------------- 写入接口 -------------------- #
    def insert_batch(
        self,
        indicators: Iterable[Dict[str, Any]],
        ts: Optional[datetime] = None,
    ) -> int:
        """
        批量写入一批指标数据

        Args:
            indicators: 来自 RealTimeStockMonitor.calculate_indicators 的字典列表
            ts: 该批数据的时间戳；如果为空则使用当前时间

        Returns:
            实际插入的行数
        """
        indicators = list(indicators)
        if not indicators:
            return 0

        ts_str = (ts or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

        rows: List[tuple] = []
        for item in indicators:
            code = item.get("股票代码")
            if not code:
                continue

            rows.append(
                (
                    code,
                    ts_str,
                    item.get("当前价格"),
                    item.get("当日最高价"),
                    item.get("当日最低价"),
                    item.get("当前涨跌幅"),
                    item.get("量比"),
                    item.get("前五日涨跌幅"),
                    item.get("上一日涨跌幅"),
                    item.get("当日开盘涨跌幅"),
                    item.get("当日最高涨跌幅"),
                    item.get("当日最低涨跌幅"),
                    item.get("当日成交量"),
                    item.get("前五日平均量"),
                )
            )

        if not rows:
            return 0

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT INTO real_time_indicators (
                    code, ts,
                    current_price, high_price, low_price,
                    current_change, volume_ratio,
                    prev_5_change, prev_day_change,
                    open_change, high_change, low_change,
                    current_volume, prev_5_volumes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            return cur.rowcount or len(rows)

    # -------------------- 查询接口 -------------------- #
    def query_by_code(
        self,
        code: str,
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
        limit: Optional[int] = None,
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        按股票代码和时间范围查询数据
        """
        where_clauses = ["code = ?"]
        params: List[Any] = [code]

        if start_ts is not None:
            where_clauses.append("ts >= ?")
            params.append(start_ts.strftime("%Y-%m-%d %H:%M:%S"))
        if end_ts is not None:
            where_clauses.append("ts <= ?")
            params.append(end_ts.strftime("%Y-%m-%d %H:%M:%S"))

        order = "ASC" if ascending else "DESC"
        sql = (
            "SELECT code, ts, current_price, high_price, low_price, "
            "current_change, volume_ratio, prev_5_change, "
            "prev_day_change, open_change, high_change, low_change, "
            "current_volume, prev_5_volumes "
            "FROM real_time_indicators "
            f"WHERE {' AND '.join(where_clauses)} "
            f"ORDER BY ts {order}"
        )

        if limit is not None and limit > 0:
            sql += " LIMIT ?"
            params.append(limit)

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
        rows = cur.fetchall()

        keys = [
            "code",
            "ts",
            "current_price",
            "high_price",
            "low_price",
            "current_change",
            "volume_ratio",
            "prev_5_change",
            "prev_day_change",
            "open_change",
            "high_change",
            "low_change",
            "current_volume",
            "prev_5_volumes",
        ]
        return [dict(zip(keys, row)) for row in rows]

    def query_latest(self, code: str) -> Optional[Dict[str, Any]]:
        """
        查询某个股票最新一条记录
        """
        results = self.query_by_code(code, limit=1, ascending=False)
        return results[0] if results else None

    def query_latest_for_codes(self, codes: Iterable[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        一次性查询多个股票的最新记录
        """
        result: Dict[str, Optional[Dict[str, Any]]] = {}
        for code in codes:
            result[code] = self.query_latest(code)
        return result

