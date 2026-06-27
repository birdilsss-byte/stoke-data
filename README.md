# 🔥 Stoke Data — A 股纯数据层

<p align="center">
  <b>零 API Key · 零注册 · 零付费 · 开箱即用</b>
</p>

<p align="center">
  <a href="https://github.com/birdilsss-byte/stoke-data"><img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python"></a>
  <a href="https://github.com/birdilsss-byte/stoke-data/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="https://github.com/birdilsss-byte/stoke-data/releases"><img src="https://img.shields.io/badge/version-2.1.2-brightgreen.svg" alt="Version"></a>
  <img src="https://img.shields.io/badge/API%20Key-不需要-orange.svg" alt="No API Key">
</p>

---

12 个数据源，覆盖 A 股行情、K 线、研报、新闻、公告、涨停、板块、估值，零 API Key。

**纯数据获取层，不含任何策略/时机/执行逻辑。**

## 3 秒开始

```bash
# 1. 安装 uv（如果还没有）
brew install uv

# 2. 克隆
git clone https://github.com/birdilsss-byte/stoke-data.git && cd stoke-data

# 3. 安装依赖
uv sync

# 4. 查实时行情
uv run python3 -c "
from stoke import Stoke
s = Stoke()
df = s.realtime(['000001', '600519'])
print(df[['symbol', 'price', 'high', 'low']].to_string())
"
```

## 用法

```python
from stoke import Stoke  # 默认带缓存

s = Stoke()

# === 数据获取 ===
df = s.kline("000001")                          # 日K线
df = s.realtime(["000001", "600519"])           # 实时行情
df = s.tencent_brief(["sh000001", "hk00700"])   # 跨市场
df = s.minute_kline("sh600519", "m30", 240)     # 分钟K线
df = s.fqkline("sh600519", "day", "hfq")        # 复权K线
df = s.intraday_line("sh600519")                # 当日分时线

# === 信号数据（列名统一）===
df = s.limit_up()                               # 涨停板
df = s.strong_stocks()                          # 强势涨停
df = s.sector_rank()                            # 行业涨跌幅排名
df = s.hot_keywords()                           # 热搜概念
df = s.northbound_flow()                        # 北向资金

# === 研报/新闻/公告 ===
df = s.research("000001")                       # 机构研报
df = s.news("000001")                           # 个股新闻
df = s.announcements_detailed("000001")         # 公告列表
df = s.download_report_pdf("infoCode")          # 下载研报PDF

# === 估值 ===
df = s.index_pe("上证50")                       # 指数 PE
df = s.market_pb()                              # 全市场 PB
df = s.eps_forecast("600519")                   # 一致预期 EPS
df = s.kline_with_valuation("sh.600000")        # K线+估值字段

# === 板块 ===
df = s.concepts()                               # 概念板块
df = s.industries()                             # 行业板块
df = s.sector_members("沪深300")                # 板块成分股
df = s.stock_industry()                         # 全市场行业分类

# === 龙虎榜 ===
df = s.dragon_tiger()                           # 龙虎榜
df = s.billboard_seat_detail("000001", "2026-01-01", "2026-06-26")
df = s.full_market_billboard("2026-06-26")

# === 检查数据来源 ===
print(df.attrs)  # → {"method": "limit_up", "fallback": False}

# === 多源备份版 ===
from stoke.fallback import FallbackStoke
fs = FallbackStoke()
df = fs.kline("000001")  # mootdx → efinance → baostock → 腾讯
```

## 特性

| 特性 | 说明 |
|------|------|
| **全局限流** | 同进程内跨实例共享限流状态，多 Agent 建议错峰调度 |
| **列名归一化** | 同方法不管走主源/备用源，返回一致列名 |
| **降级透明** | `df.attrs` 标记 method + fallback 信息，调用方可感知 |
| **SQLite 缓存** | 分级 TTL，缓存命中 <10ms，故障自动回退旧缓存 |
| **多源备份** | 核心方法 2-4 级 fallback 链，东财崩了走同花顺 |

## 12 数据源

| 数据源 | 协议 | 限流 | 覆盖 |
|--------|------|:----:|------|
| mootdx | TCP 通达信 | 不限 | K线、实时行情、指数、板块成分股、F10 |
| akshare | HTTP 东财/同花顺 | 5s | 新闻、研报、涨停、情绪、资金流、行业 |
| baostock | HTTP 证券宝 | 1s | 复权K线、行业分类、股票列表、财报 |
| efinance | HTTP 新浪/网易/东财 | 0.5s | 极速K线、龙虎榜、十大股东、资金流 |
| legulegu | HTTP 乐咕乐股 | 1s | PE/PB 估值 |
| tencent_direct | HTTP 腾讯 qt.gtimg.cn | 0.3s | 实时行情、K线、分钟K线、复权、跨市场 |
| eastmoney | HTTP 东财 reportapi | 1.5s | 个股研报、行业研报、PDF 下载 |
| ths | HTTP 同花顺 10jqka | 1s | 机构一致预期 EPS |
| datacenter | HTTP 东财 datacenter | 1.5s | 龙虎榜席位明细、全市场龙虎榜 |
| cninfo | HTTP 东财公告 | 1s | 沪深北公告列表 |
| push2 | HTTP 东财 push2 | 1s | 行业板块排名、概念板块排名（akshare 降级备用） |
| ths_hot | HTTP 同花顺热点 | 0.5s | 强势股+题材归因、涨停板近似（akshare 降级备用） |

## 限流规则

| 数据源 | 间隔 | 说明 |
|--------|:----:|------|
| mootdx | 不限 | TCP 协议 |
| akshare | **5 秒** | 最严格 |
| tencent_direct | 0.3 秒 | 腾讯直连 |
| 其余 9 源 | 0.5-1.5 秒 | 内置自动 |

## 降级链

```
limit_up()        → akshare ─┬→ ths_hot
strong_stocks()   → akshare ─┬→ ths_hot
sector_rank()     → akshare ─┬→ push2
northbound_flow() → akshare ─┬→ ths_hot
hot_keywords()    → akshare ─┬→ push2
kline()           → mootdx ──┬→ efinance ──┬→ baostock ──┬→ 腾讯
realtime()        → mootdx ──┬→ 腾讯 ──────┬→ 新浪 ──────┬→ efinance
```

## 许可证

MIT

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/birdilsss-byte">birdilsss-byte</a></sub>
</p>
