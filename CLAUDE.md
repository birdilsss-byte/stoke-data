# Stoke Data — A股量化数据层（精简版）

## 项目定位

Stoke 主仓库的数据层子集。纯粹的数据获取层，**无策略/时机/执行逻辑**，可被其他模块或智能体自由复用。

## 数据源（10 源 + 2 备用）

| 数据源 | 协议 | 限流 | 覆盖层面 |
|--------|------|------|---------|
| mootdx | TCP（通达信） | 不限 | K线、实时行情、指数、板块成分股、F10 |
| akshare | HTTP（东财/同花顺） | 5s | 新闻、研报、涨停、情绪、资金流、行业板块 |
| baostock | HTTP（证券宝） | 1s | 复权K线、行业分类、股票列表 |
| efinance | HTTP（新浪/网易/东财） | 0.5s | 极速K线、龙虎榜、十大股东、股东人数 |
| legulegu | HTTP（乐咕乐股） | 1s | PE/PB 估值 |
| tencent_direct | HTTP（腾讯 qt.gtimg.cn） | 0.3s | 实时行情 + K 线，毫秒级 |
| eastmoney | HTTP（东财 reportapi） | 1.5s | 个股研报、行业研报、PDF 下载 |
| ths | HTTP（同花顺 10jqka） | 1s | 机构一致预期 EPS |
| datacenter | HTTP（东财 datacenter） | 1.5s | 龙虎榜席位明细、全市场龙虎榜 |
| cninfo | HTTP（东财公告） | 1s | 沪深北公告列表 |
| 新浪直连 | HTTP（hq.sinajs.cn） | — | FallbackStoke 备用实时行情 |
| 智兔数服 | REST API | 1s | 备用行情、技术指标（需 Token） |

## 项目结构

```
stock-data/
├── stoke/
│   ├── __init__.py           # StokeCached + FallbackStoke
│   ├── client.py             # Stoke 纯路由（裸版，无缓存）
│   ├── client_cached.py      # StokeCached 缓存包装
│   ├── store.py              # SQLite 缓存（get_or_fetch）
│   ├── fallback.py           # FallbackStoke 多源自动备份
│   ├── probe.py              # 前导探路（数据源健康探测）
│   ├── config.py             # 限流 + 日志系统
│   ├── calendar.py           # A 股交易日历
│   ├── rate_limiter.py       # 限流器
│   ├── utils.py              # 工具函数
│   ├── exceptions.py         # 异常定义
│   └── sources/              # 10 源适配器
│       ├── mootdx_source.py
│       ├── akshare_source.py
│       ├── baostock_source.py
│       ├── efinance_source.py
│       ├── legulegu_source.py
│       ├── tencent_direct_source.py
│       ├── eastmoney_source.py
│       ├── ths_source.py
│       ├── datacenter_source.py
│       └── cninfo_source.py
├── tests/
├── pyproject.toml
└── CLAUDE.md
```

## 核心原则

1. **限流是铁律** — 每个数据源必须遵守调用间隔
2. **保持简单** — 每文件一个类，不过度抽象
3. **health_check() 必实现** — 每个 Source 都要能快速验证连通性
4. **返回 DataFrame** — 行情/K线/公告统一用 DataFrame
5. **多源备份** — FallbackStoke 为主方法提供 2-4 级 fallback 链

## 编码规范

- Python 3.11+，UTF-8，中文注释
- 包管理用 `uv`（`uv add` / `uv run`），不用 pip
- 代码加注释，面向编程初学者
- 环境：Mac M4 芯片

## 安全红线

- **绝对禁止**明文暴露 API Token/密码/Key
- 密钥从环境变量或配置文件读取

## Git

- 这是 Stoke 主仓库的一个 **worktree**（分支 `experiment/stock-data`），不要直接 push
- 改动需在 Stoke 主仓库的 `dev/next` 开发，合并后同步过来
- 实验性功能在此验证，稳定后合并回主仓库

## 用法速查

```python
from stoke import Stoke  # 默认带缓存
s = Stoke()
df = s.kline("000001")          # 日K线
df = s.realtime(["000001"])     # 实时行情
df = s.limit_up("20260626")     # 涨停板
df = s.sector_rank()            # 行业涨跌幅排名
df = s.stock_list()             # 全市场股票列表

from stoke.fallback import FallbackStoke  # 多源备份版
fs = FallbackStoke()
df = fs.kline("000001")  # mootdx → efinance → baostock → 腾讯
```
