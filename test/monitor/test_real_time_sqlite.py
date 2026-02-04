#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实时监控SQLite存储模块
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def _build_sample_indicators():
    """构造与 RealTimeStockMonitor.calculate_indicators 一致结构的示例数据"""
    return [
        {
            "股票代码": "000001",
            "股票名称": "平安银行",
            "当前价格": 10.5,
            "当日最高价": 11.0,
            "当日最低价": 10.0,
            "当前涨跌幅": 1.5,
            "量比": 1.2,
            "前五日涨跌幅": 0.8,
            "上一日涨跌幅": 1.0,
            "当日开盘涨跌幅": 0.5,
            "当日最高涨跌幅": 2.0,
            "当日最低涨跌幅": -1.0,
            "当日成交量": 1000000,
            "前五日平均量": 800000,
        },
        {
            "股票代码": "000002",
            "股票名称": "万科A",
            "当前价格": 20.0,
            "当日最高价": 20.5,
            "当日最低价": 19.5,
            "当前涨跌幅": -2.0,
            "量比": 0.9,
            "前五日涨跌幅": -0.5,
            "上一日涨跌幅": -1.5,
            "当日开盘涨跌幅": -1.0,
            "当日最高涨跌幅": 0.5,
            "当日最低涨跌幅": -2.5,
            "当日成交量": 500000,
            "前五日平均量": 600000,
        },
    ]


def test_sqlite_basic_rw(tmp_path=None):
    """测试SQLite基本读写功能"""
    from monitor.real_time_sqlite import RealTimeMonitorSQLite

    # 使用临时目录，避免污染真实缓存目录
    if tmp_path is None:
        tmp_dir = Path("/tmp/cache_output/quantara/test_sqlite")
        tmp_dir.mkdir(parents=True, exist_ok=True)
    else:
        tmp_dir = Path(tmp_path)

    db_path = tmp_dir / "real_time_monitor_test.db"

    # 确保干净环境
    if db_path.exists():
        db_path.unlink()

    storage = RealTimeMonitorSQLite(db_path)

    indicators = _build_sample_indicators()
    now = datetime.now()
    inserted = storage.insert_batch(indicators, ts=now)

    assert inserted == len(indicators), "插入的行数应与数据条数一致"

    # 查询单个code
    res_1 = storage.query_by_code("000001")
    assert len(res_1) == 1, "代码000001应有1条记录"
    row_1 = res_1[0]
    assert row_1["code"] == "000001"
    assert row_1["current_price"] == 10.5
    assert row_1["high_price"] == 11.0
    assert row_1["low_price"] == 10.0
    # 不应包含股票名称
    assert "股票名称" not in row_1

    # 时间范围查询
    start = now - timedelta(minutes=1)
    end = now + timedelta(minutes=1)
    res_range = storage.query_by_code("000001", start_ts=start, end_ts=end)
    assert len(res_range) == 1, "时间范围内应能查询到记录"

    # 最新记录查询
    latest = storage.query_latest("000001")
    assert latest is not None, "最新记录不应为空"
    assert latest["code"] == "000001"

    # 多股票最新记录
    latest_multi = storage.query_latest_for_codes(["000001", "000002", "000003"])
    assert "000001" in latest_multi and "000002" in latest_multi and "000003" in latest_multi
    assert latest_multi["000001"] is not None
    assert latest_multi["000002"] is not None
    # 未写入的代码应返回None
    assert latest_multi["000003"] is None


def test_monitor_integration_sqlite():
    """简单验证 RealTimeStockMonitor 能创建 sqlite 存储实例"""
    from monitor.real_time_monitor import RealTimeStockMonitor

    monitor = RealTimeStockMonitor()
    assert monitor.sqlite_storage is not None
    assert monitor.sqlite_db_path.exists() or monitor.sqlite_db_path.parent.exists()

