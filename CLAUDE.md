# Stoke Data — A 股纯数据层

## 🔴 绝对红线

**这个项目只做一件事：获取 A 股数据并返回。**
- ❌ 不做策略（没有发现层）
- ❌ 不做时机判断（没有 timing）
- ❌ 不做交易执行（没有 execute/runner）
- ❌ 不做持仓管理
- ❌ 不做复盘/经验沉淀
- ✅ **只做：12 源 → 路由 → 缓存 → 限流 → 归一化 → 返回 DataFrame**

任何往这个项目里加策略/扫描/交易逻辑的行为，都是越界。策略逻辑应该写在调用方的项目里（如 `stock-avenger`）。

---

## 定位

`stoke-data` 是一个独立的 A 股数据获取库，可被 Claude Code Agent、Python 脚本、或其他项目作为依赖调用。

- 独立仓库：`birdilsss-byte/stoke-data`
- 本地路径：`~/Documents/stock-data/`
- 包名：`stoke-data` v2.0.0
- 许可证：MIT

---

## 数据源（12 源）

| 数据源 | 协议 | 限流 | 覆盖 |
|--------|------|:----:|------|
| mootdx | TCP 通达信 | 不限 | K线、实时行情、指数、板块成分股、F10 |
| akshare | HTTP 东财/同花顺 | 5s | 新闻、研报、涨停、情绪、资金流、行业 |
| baostock | HTTP 证券宝 | 1s | 复权K线、行业分类、股票列表、财报 |
| efinance | HTTP 新浪/网易/东财 | 0.5s | 极速K线、龙虎榜、十大股东、资金流 |
| legulegu | HTTP 乐咕乐股 | 1s | PE/PB 估值 |
| tencent_direct | HTTP 腾讯 qt.gtimg.cn | 0.3s | 实时行情、K线（日/周/月/分钟）、复权、跨市场 |
| eastmoney | HTTP 东财 reportapi | 1.5s | 个股研报、行业研报、PDF 下载 |
| ths | HTTP 同花顺 10jqka | 1s | 机构一致预期 EPS |
| datacenter | HTTP 东财 datacenter | 1.5s | 龙虎榜席位明细、全市场龙虎榜 |
| cninfo | HTTP 东财公告 | 1s | 沪深北公告列表 |
| **push2** | HTTP 东财 push2 | 1s | 行业板块排名、概念板块排名（akshare 降级备用） |
| **ths_hot** | HTTP 同花顺热点 | 0.5s | 强势股+题材归因、涨停板近似、北向资金（akshare 降级备用） |

---

## 项目结构

```
stock-data/
├── stoke/
│   ├── __init__.py           # 导出 Stoke + FallbackStoke + 异常类
│   ├── client.py             # 12 源统一路由 + 列名归一化
│   ├── client_cached.py      # SQLite 缓存包装
│   ├── store.py              # 缓存存储（16 表，分级 TTL）
│   ├── fallback.py           # FallbackStoke 多源自动备份
│   ├── config.py             # 限流配置 + RateLimiter（全局共享）
│   ├── calendar.py           # A 股交易日历
│   ├── utils.py              # 指数退避重试
│   └── sources/              # 12 数据源适配器
│       ├── mootdx_source.py
│       ├── akshare_source.py
│       ├── baostock_source.py
│       ├── efinance_source.py
│       ├── legulegu_source.py
│       ├── tencent_direct_source.py
│       ├── eastmoney_source.py
│       ├── ths_source.py
│       ├── datacenter_source.py
│       ├── cninfo_source.py
│       ├── push2_source.py       # ★ 东财 push2（akshare 降级）
│       └── ths_hot_source.py     # ★ 同花顺热点（akshare 降级）
├── tests/
├── pyproject.toml
├── CLAUDE.md
└── SKILL.md
```

---

## 核心特性

### 全局限流
多 Agent/多模块同时调用同一数据源时，跨实例共享限流状态，自动协调间隔，避免 IP 封禁。

```python
# Agent A 和 Agent B 同时调 akshare，限流器自动协调，不会 5 秒内发两次
```

### 列名归一化
同一方法不管走主源还是降级备用源，返回一致的列名。

```python
df = s.limit_up()
# 列名统一：symbol, name, change_pct, board_days, reason, industry
# 不论数据来自 akshare 还是 ths_hot，列名一样
```

### 降级透明
`df.attrs` 携带数据来源信息，调用方可自主判断是否可信。

```python
df = s.limit_up()
df.attrs["method"]    # → "limit_up"
df.attrs["fallback"]  # → True/False（是否走了备用源）
```

### 降级链

```
limit_up()        → akshare ─┬→ ths_hot
strong_stocks()   → akshare ─┬→ ths_hot
sector_rank()     → akshare ─┬→ push2
northbound_flow() → akshare ─┬→ ths_hot
hot_keywords()    → akshare ─┬→ push2
kline()           → mootdx ──┬→ efinance ──┬→ baostock ──┬→ 腾讯直连
realtime()        → mootdx ──┬→ 腾讯直连 ──┬→ 新浪直连 ──┬→ efinance
```

---

## 用法

```python
from stoke import Stoke  # 默认带缓存

s = Stoke()

# === 数据获取 ===
df = s.kline("000001")                  # 日K线
df = s.realtime(["000001", "600519"])   # 实时行情
df = s.tencent_brief(["sh000001", "hk00700"])  # 跨市场
df = s.minute_kline("sh600519", "m30", 240)     # 分钟K线

# === 信号数据（列名统一）===
df = s.limit_up()          # 涨停板
df = s.strong_stocks()     # 强势涨停
df = s.sector_rank()       # 行业涨跌幅排名
df = s.hot_keywords()      # 热搜概念
df = s.northbound_flow()   # 北向资金

# === 研报/新闻/公告 ===
df = s.research("000001")       # 机构研报
df = s.news("000001")           # 个股新闻
df = s.announcements_detailed("000001")  # 公告列表

# === 估值 ===
df = s.index_pe("上证50")       # 指数 PE
df = s.market_pb()              # 全市场 PB
df = s.eps_forecast("600519")   # 一致预期 EPS

# === 板块 ===
df = s.concepts()               # 概念板块
df = s.industries()             # 行业板块
df = s.sector_members("沪深300")  # 板块成分股
df = s.stock_industry()          # 全市场行业分类

# === 检查数据来源 ===
print(df.attrs)  # → {"method": "limit_up", "fallback": False}

from stoke.fallback import FallbackStoke  # 多源备份版
fs = FallbackStoke()
df = fs.kline("000001")  # mootdx → efinance → baostock → 腾讯
```

---

## 编码规范

- Python 3.11+，UTF-8，中文注释
- 包管理用 `uv`（`uv add` / `uv run`），不用 pip
- 每文件一个类，不过度抽象
- 代码加注释，面向编程初学者
- health_check() 必实现

## 安全红线

- **绝对禁止**明文暴露 API Token/密码/Key
- 密钥从环境变量或配置文件读取，不得内联

## Git

独立仓库：`git@github.com:birdilsss-byte/stoke-data.git`
