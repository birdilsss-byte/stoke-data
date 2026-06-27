# Stoke Data — A 股纯数据层

工作目录: `~/Documents/stock-data/` — 操作前先 cd 到这里。
依赖安装完，无需重复 `uv sync`。调数据前无需设 STOKE_HOME。

---

## 定位

纯数据获取库。可被 Claude Code Agent、Python 脚本或其他项目调用。

- 仓库：`birdilsss-byte/stoke-data`
- 包名：`stoke-data` v2.1.0 | MIT

---

## 数据源（12 源）（不断增加中）

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

## 核心特性

### 全局限流
多 Agent/多模块同时调用同一数据源时，跨实例共享限流状态，限流器自动协调间隔，避免 IP 封禁。

### 列名归一化
同一方法不管走主源还是降级备用源，返回一致的列名。

### 降级透明
`df.attrs` 携带数据来源信息，调用方可自主判断是否可信。

---

---

## 当前状态

✅ 稳定 — 12 源 + 缓存 + 全局限流 + 列名归一化 + 降级链。日常可用。
⬜ 下一步：更多数据源、更细粒度降级链覆盖（当前 5 条，部分 akshare 方法无备用）

## 编码规范

- Python 3.11+，UTF-8，中文注释
- 包管理用 `uv`（`uv add` / `uv run`），不用 pip
- 每文件一个类，不过度抽象
- 代码加注释，面向编程初学者
- health_check() 必实现

## 安全红线

- **绝对禁止**明文暴露 API Token/密码/Key
- 密钥从环境变量或配置文件读取，不得内联

