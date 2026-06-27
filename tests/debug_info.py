"""
Stoke 调试信息打印
快速查看版本、配置、缓存状态、环境信息
用法: uv run python3 tests/debug_info.py
"""

import sys
import os
import platform
from datetime import datetime


def main():
    print(f"=== Stoke 调试信息 === ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  Python:   {sys.version.split()[0]}")
    print(f"  工作目录: {os.getcwd()}")

    # 版本
    import stoke
    print(f"  stoke:    v{stoke.__version__}")
    print(f"  __all__:  {stoke.__all__}")

    # 限流配置
    from stoke.config import RATE_LIMIT
    print(f"\n--- 限流配置 ---")
    for name, interval in sorted(RATE_LIMIT.items()):
        print(f"  {name:<20s} {interval:>5.1f}s")

    # 缓存状态
    print(f"\n--- 缓存状态 ---")
    from stoke import Stoke
    s = Stoke()
    stats = s.store.stats()
    if stats:
        total = sum(stats.values())
        print(f"  数据库: .stoke_cache.db")
        print(f"  表数:   {len(stats)}")
        print(f"  总行数: {total:,}")
        print(f"\n  明细:")
        for table, count in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"    {table:<25s} {count:>8,} 行")
    else:
        print(f"  缓存为空（首次使用正常）")

    # WAL 检查
    import sqlite3
    try:
        conn = sqlite3.connect(".stoke_cache.db")
        jm = conn.execute("PRAGMA journal_mode").fetchone()[0]
        print(f"\n  journal_mode: {jm}")
        conn.close()
    except Exception:
        pass

    # 数据源连通性 (可选)
    if "--health" in sys.argv:
        print(f"\n--- 全源连通性 ---")
        try:
            result = s.health_check()
            for name, alive in result.items():
                print(f"  {'✅' if alive else '❌'} {name}")
        except Exception as e:
            print(f"  检查失败: {e}")

    print(f"\n  提示: uv run python3 tests/debug_info.py --health  检查全源连通性")
    print(f"         uv run python3 tests/smoke_test.py          运行冒烟测试\n")


if __name__ == "__main__":
    main()
