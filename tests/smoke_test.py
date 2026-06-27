"""
Stoke 快速冒烟测试
覆盖 12 个数据源的关键方法，验证列名和 attrs 标记
用法: uv run python3 tests/smoke_test.py
"""

import sys
import time
from datetime import datetime

import pandas as pd

from stoke import Stoke
from stoke.fallback import FallbackStoke


def main():
    s = Stoke()
    fs = FallbackStoke()
    results = []

    def test(name, fn, expect_cols=None, min_rows=1, allow_empty=False):
        start = time.time()
        try:
            data = fn()
            elapsed = round(time.time() - start, 2)

            if isinstance(data, pd.DataFrame):
                rows, cols = len(data), data.columns.tolist()
                attrs = dict(data.attrs)

                # 检查 attrs
                has_method = "method" in attrs
                has_fallback = "fallback" in attrs

                # 检查列名
                col_ok = True
                missing = []
                if expect_cols:
                    missing = [c for c in expect_cols if c not in cols]
                    col_ok = len(missing) == 0

                if rows == 0 and not allow_empty:
                    results.append({"name": name, "status": "WARN", "time": elapsed,
                                    "msg": f"空数据 {rows}行", "attrs": attrs})
                elif col_ok:
                    results.append({"name": name, "status": "PASS", "time": elapsed,
                                    "msg": f"{rows}行 {len(cols)}列 attrs={{{'method' if has_method else '?'}{', fallback' if has_fallback else ''}}}",
                                    "missing": missing, "attrs": attrs})
                else:
                    results.append({"name": name, "status": "FAIL", "time": elapsed,
                                    "msg": f"缺列: {missing}", "attrs": attrs})
            else:
                results.append({"name": name, "status": "PASS", "time": elapsed,
                                "msg": f"type={type(data).__name__}", "attrs": {}})
        except Exception as e:
            elapsed = round(time.time() - start, 2)
            results.append({"name": name, "status": "FAIL", "time": elapsed,
                            "msg": f"{type(e).__name__}: {str(e)[:80]}", "attrs": {}})

    # ===== mootdx (行情) =====
    test("realtime",           lambda: s.realtime(["000001"]),
         expect_cols=["symbol", "price", "high", "low"])
    test("kline (日线)",       lambda: s.kline("000001"),
         expect_cols=["open", "high", "low", "close", "volume"])
    test("stock_list",         lambda: s.stock_list(), min_rows=1000)

    # ===== akshare (新闻/研报/公告) =====
    test("news",               lambda: s.news("000001"), min_rows=1)
    test("telegraph",          lambda: s.telegraph(), min_rows=1, allow_empty=True)
    test("research",           lambda: s.research("000001"), min_rows=0, allow_empty=True)
    test("announcements",      lambda: s.announcements("000001"), min_rows=1)

    # ===== akshare (信号) =====
    test("limit_up",           lambda: s.limit_up(), min_rows=0, allow_empty=True,
         expect_cols=["symbol", "name", "change_pct"])
    test("strong_stocks",      lambda: s.strong_stocks(), min_rows=0, allow_empty=True,
         expect_cols=["symbol", "name", "change_pct"])
    test("limit_down",         lambda: s.limit_down(), min_rows=0, allow_empty=True)

    # ===== akshare (板块) =====
    test("concepts",           lambda: s.concepts(), min_rows=0, allow_empty=True)
    test("industries",         lambda: s.industries(), min_rows=0, allow_empty=True)
    test("sector_rank",        lambda: s.sector_rank(), min_rows=0, allow_empty=True,
         expect_cols=["sector_name", "change_pct"])
    test("sector_members",     lambda: s.sector_members("沪深300"), min_rows=10)
    test("stock_comment_all",  lambda: s.stock_comment_all(), min_rows=0, allow_empty=True,
         expect_cols=["symbol", "name", "score"])

    # ===== akshare (资金流) =====
    test("northbound_flow",    lambda: s.northbound_flow(),
         expect_cols=["date", "net_buy"])
    test("dragon_tiger",       lambda: s.dragon_tiger(), min_rows=0, allow_empty=True)
    test("market_fund_flow",   lambda: s.market_fund_flow(), min_rows=1)
    test("individual_fund_flow", lambda: s.individual_fund_flow("000001"), min_rows=1)
    test("margin_shanghai",    lambda: s.margin_shanghai(), min_rows=1)

    # ===== akshare (情绪) =====
    test("hot_detail",         lambda: s.hot_detail("000001"), min_rows=0, allow_empty=True)
    test("hot_keywords",       lambda: s.hot_keywords(), min_rows=0, allow_empty=True,
         expect_cols=["symbol", "concept_name", "heat"])
    test("xueqiu_hot",         lambda: s.xueqiu_hot(), min_rows=0, allow_empty=True)

    # ===== legulegu (估值) =====
    test("index_pe (上证50)",  lambda: s.index_pe("上证50"), min_rows=10)
    test("market_pb",          lambda: s.market_pb(), min_rows=10)

    # ===== tencent_direct =====
    test("market_realtime",    lambda: s.market_realtime(["sh000001"]),
         expect_cols=["symbol", "price"])

    # ===== FallbackStoke =====
    test("[Fallback] kline",   lambda: fs.kline("000001"), min_rows=100)
    test("[Fallback] realtime", lambda: fs.realtime(["000001"]),
         expect_cols=["symbol", "price", "high", "low"])

    # ===== 缓存 =====
    cache = s.store.stats()
    if cache:
        total_rows = sum(cache.values())
        results.append({"name": "cache stats", "status": "PASS", "time": 0,
                        "msg": f"{len(cache)}张表 {total_rows}行", "attrs": {}})
    else:
        results.append({"name": "cache stats", "status": "WARN", "time": 0,
                        "msg": "缓存为空 (首次运行正常)", "attrs": {}})

    # ===== 输出 =====
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total_time = sum(r["time"] for r in results)

    print(f"\n{'='*65}")
    print(f"  Stoke v2.1.2 冒烟测试  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*65}")
    for r in results:
        icon = {"PASS": "  ", "WARN": "!!", "FAIL": "XX"}[r["status"]]
        print(f"  [{icon}] {r['name']:<30s} {r['time']:>6.2f}s  {r['msg']}")

    print(f"{'='*65}")
    print(f"  通过: {passed}  告警: {warned}  失败: {failed}  总耗时: {total_time:.1f}s")

    if failed:
        print(f"\n  失败项详情:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    - {r['name']}: {r['msg']}")

    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
