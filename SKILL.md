---
name: stoke
description: |
  🔥 免费 A 股数据层 — 零 API Key、零注册、零付费，开箱即用。
  12 源 + 缓存 + 自动降级，统一列名，多 Agent 全局限流。
  当用户提到"股票"、"行情"、"K线"、"涨停"、"强势股"、"研报"、"PE"、"PB"、"估值"、
  "个股新闻"、"公告"、"题材"、"概念板块"、"行业板块"、"财联社"、"电报"、"A股"时触发。
  也用于查某只股票的实时价格、历史K线、财务研报、新闻公告等。
homepage: https://github.com/birdilsss-byte/stoke
platforms: [macos, windows]
metadata:
  openclaw:
    emoji: 🔥
    requires: {}
    install:
      uv:
        - akshare
        - baostock
        - beautifulsoup4
        - efinance
        - mootdx
        - pandas
        - requests
  hermes:
    tags: [stock, finance, a-share, market-data, quant, free, zero-api-key]
    category: finance
    requires:
      bins:
        - python3
        - uv
    install:
      uv: [akshare, baostock, beautifulsoup4, efinance, mootdx, pandas, requests]
    postinstall: "cd $STOKE_HOME && uv sync --no-cache --python-preference only-managed && uv run python3 -c \"from stoke import Stoke; print('OK')\""
---

# Stoke Data — A 股数据层（精简版）

纯数据获取层，**零 API Key**，所有数据源免注册。

## ✨ 更新亮点

| 特性 | 说明 |
|------|------|
| **全局限流** | 多 Agent 同时调用同一数据源，自动协调间隔，不再封 IP |
| **列名统一** | 不管走哪个源，同方法的列名一致（如 `limit_up()` 返回 `symbol/name/change_pct`）|
| **降级透明** | `df.attrs["fallback"]` 标记数据是否来自备用源，消费者可感知 |
| **12 源** | akshare→push2/ths_hot 自动降级，东财被封走同花顺 |

## 3 秒开始

```bash
# 1. 设 STOKE_HOME
export STOKE_HOME=~/Documents/stock-data

# 2. 安装依赖
cd $STOKE_HOME && uv sync

# 3. 查实时行情
uv run python3 -c "
from stoke import Stoke
s = Stoke()
df = s.realtime(['000001', '600000', '000858'])
print(df[['symbol', 'price', 'high', 'low', 'vol']].to_string())
"
```

## 用法速查

```python
from stoke import Stoke
s = Stoke()

# 行情
df = s.realtime(["000001", "600519"])       # 实时行情
df = s.kline("000001")                       # 日K线
df = s.tencent_brief(["sh000001", "hk00700"]) # 跨市场（A/港/美）
df = s.minute_kline("sh600519", "m30", 240)  # 分钟K线

# 信号（列名已归一化，不挑源）
df = s.limit_up()                            # 涨停板
# df 列: symbol, name, change_pct, board_days, reason, industry
df = s.strong_stocks()                       # 强势涨停
df = s.sector_rank()                         # 行业涨跌幅排名
df = s.hot_keywords()                        # 热搜概念
df = s.northbound_flow()                     # 北向资金

# 研报/新闻/公告
df = s.research("000001")                    # 机构研报
df = s.news("000001")                        # 个股新闻
df = s.announcements_detailed("000001")      # 巨潮公告

# 估值
df = s.index_pe("上证50")                    # 指数 PE
df = s.market_pb()                           # 全市场 PB
df = s.eps_forecast("600519")                # 一致预期 EPS

# 板块
df = s.concepts()                            # 概念板块列表
df = s.industries()                          # 行业板块列表
df = s.sector_members("沪深300")             # 板块成分股

# 检测数据来源（新特性）
print(df.attrs)  # → {"method": "limit_up", "fallback": False}
# fallback=True 说明主源不可用，走的是备用源
```
 > 注：`s.*` 调用走透明代理（`StokeCached.__getattr__`→裸 `Stoke`），未列出的方法同样可用。
 > 重要数据推荐 `FallbackStoke`（多级自动备份）：`from stoke import FallbackStoke; fb = FallbackStoke(); fb.kline("000001")`
 > 💡 **多 Agent 提示**：多个 Agent 同时使用时错开 akshare 调用（间隔 ≥5s），避免同时请求。缓存 SQLite 已启用 WAL 模式，支持并发读写。

## 降级链速查

```
limit_up()        → akshare ─┬→ ths_hot      (同花顺涨停板近似)
strong_stocks()   → akshare ─┬→ ths_hot      (同花顺强势股+题材)
sector_rank()     → akshare ─┬→ push2        (东财官方 API)
northbound_flow() → akshare ─┬→ ths_hot      (北向资金)
hot_keywords()    → akshare ─┬→ push2        (概念板块排名)
kline()           → mootdx ──┬→ efinance ──┬→ baostock ──┬→ 腾讯直连
realtime()        → mootdx ──┬→ 腾讯直连 ──┬→ 新浪直连 ──┬→ efinance
```

## 限流规则

| 数据源 | 间隔 | 说明 |
|--------|:----:|------|
| mootdx | 不限 | TCP 协议 |
| akshare | **5 秒** | 最严格 |
| tencent_direct | 0.3 秒 | 腾讯直连 |
| 其余 9 源 | 0.5-1.5 秒 | 内置自动 |

## Stoke Home 路径

```bash
export STOKE_HOME=~/Documents/stock-data
```

当前安装位置：`~/Documents/stock-data/`，这是 Stoke 主仓库的 worktree（分支 `experiment/stock-data`），只含数据层，不含策略/时机/执行逻辑。

## 测试与调试

```bash
uv run python3 tests/smoke_test.py        # 冒烟测试（30+ 方法，检查列名和 attrs）
uv run python3 tests/debug_info.py        # 查看版本、配置、缓存状态
uv run python3 tests/debug_info.py --health  # 含全源连通性
uv run python3 scripts/verify_install.py  # 验证安装和依赖
uv run python3 tests/stress_test.py       # 40 项全接口压力测试（生成 HTML 报告）
```
