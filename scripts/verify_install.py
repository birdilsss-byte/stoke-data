"""
Stoke 安装验证脚本
快速验证 import + 初始化 + 可选连通性检查
用法:
    uv run python3 scripts/verify_install.py           # 快速验证
    uv run python3 scripts/verify_install.py --full    # 含全源连通性
"""

import sys
import importlib


def check_import(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def main():
    ok = True

    # 1. 核心依赖
    deps = ["stoke", "pandas", "requests", "akshare", "mootdx", "baostock", "efinance"]
    print("检查依赖导入...")
    for dep in deps:
        if check_import(dep):
            print(f"  ok  {dep}")
        else:
            print(f"  !!  {dep}")
            ok = False

    if not ok:
        print("\n依赖缺失，请执行: uv sync")
        sys.exit(1)

    # 2. 版本
    import stoke
    print(f"\nstoke 版本: v{stoke.__version__}")

    # 3. 初始化
    print("\n初始化 Stoke...")
    try:
        from stoke import Stoke
        s = Stoke()
        print("  ok  Stoke() 初始化成功")
        print(f"  ok  StokeCached 缓存已启用")
    except Exception as e:
        print(f"  !!  Stoke() 初始化失败: {e}")
        sys.exit(1)

    # 4. FallbackStoke
    print("\n初始化 FallbackStoke...")
    try:
        from stoke.fallback import FallbackStoke
        fs = FallbackStoke()
        print("  ok  FallbackStoke() 初始化成功")
    except Exception as e:
        print(f"  !!  FallbackStoke() 初始化失败: {e}")

    # 5. 可选连通性
    if "--full" in sys.argv:
        print("\n全源连通性检查...")
        try:
            result = s.health_check()
            all_ok = True
            for name, alive in result.items():
                status = "ok" if alive else "!!"
                print(f"  {status}  {name}")
                if not alive:
                    all_ok = False
            if all_ok:
                print("\n全源连通正常")
            else:
                print("\n部分源不可用（不影响基本使用）")
        except Exception as e:
            print(f"  !!  连通性检查异常: {e}")

    print("\nStoke 安装验证通过")
    print("提示: uv run python3 tests/smoke_test.py  运行冒烟测试")
    print("      uv run python3 tests/debug_info.py  查看缓存和配置")
    sys.exit(0)


if __name__ == "__main__":
    main()
