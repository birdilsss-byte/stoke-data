# Stoke v1.3.0 安装测试报告 — 三尺

> 测试时间：2026-06-27 15:00 CST  
> 测试环境：macOS 25.5.0 (arm64)、Python 3.12.13、uv  
> 测试者：三尺

---

## 一、安装结果

| 项目 | 状态 |
|------|:----:|
| zip 解压 | ✅ |
| `uv sync` 依赖安装 | ✅ |
| `from stoke import Stoke` 导入 | ✅ |
| 全源连通性 (6/6) | ✅ |

---

## 二、数据源逐项测试

### 2.1 mootdx（通达信 TCP）— ✅ 全部通过

| 方法 | 结果 |
|------|:--:|
| `health_check()` | ✅ |
| `get_realtime(["000001","600000"])` | ✅ |
| `get_kline("000001")` | ✅ |
| `get_stock_list()` | ✅ |

### 2.2 akshare（东财/同花顺/巨潮）— ⚠️ 1 项超时

| 方法 | 结果 |
|------|:--:|
| `get_news("000001")` | ✅ |
| `get_limit_up_pool("20260626")` | ✅ 60 只涨停 |
| `get_strong_stocks("20260626")` | ✅ 281 只，含题材归因 |
| `get_research_report("000001")` | ✅ 225 篇研报 |
| `get_announcements("000001")` | ✅ 1736 条 |
| `get_concept_list()` | ✅ 373 板块 |
| `get_industry_list()` | ✅ 90 行业 |
| `get_cls_telegraph()` | ❌ **超时** >3分钟无响应 |

### 2.3 legulegu（乐咕乐股）— ✅ 通过

| 方法 | 结果 |
|------|:--:|
| `get_index_pe("上证50")` | ✅ 5214 条 |
| `get_market_pb()` | ✅ 5208 条 |

### 2.4 腾讯直连（qt.gtimg.cn）— ✅ 通过

| 方法 | 结果 |
|------|:--:|
| `get_realtime(["000001","600519"])` | ✅ 毫秒级 |
| `get_kline("000001")` | ✅ 640 条 |

### 2.5 efinance — ✅ 通过

| 方法 | 结果 |
|------|:--:|
| `get_realtime_all()` | ✅ 5867 只 |
| `get_capital_flow("600519")` | ✅ |
| `get_sector_members("600519")` | ✅ |

### 2.6 baostock — ✅ 通过

| 方法 | 结果 |
|------|:--:|
| K线+估值 | ✅ PE/PB/PS/PCF |
| 季度盈利能力 | ✅ ROE/净利率/EPS |
| 指数成分股 | ✅ 沪深300 |

---

## 三、统一入口测试

| 门面类 | 结果 |
|--------|:--:|
| `Stoke()` | ✅ 6源路由 + SQLite缓存 |
| `FallbackStoke()` | ✅ 6/6源存活 |

---

## 四、发现的问题

### 🔴 严重

1. **财联社电报 `get_cls_telegraph()` 超时无响应**
   - akshare `stock_info_global_cls()` 调用卡死 >3分钟
   - 建议：加 timeout 保护，或换用备份接口

### 🟡 中等

2. **SKILL.md 文档列名与实际代码不匹配**
   - 文档写 `pe["分位点"]`，实际无此列，列名是 `静态市盈率`、`滚动市盈率` 等

3. **SKILL.md 类名大小写错误**
   - 文档写 `EfinanceSource`，实际 `EFinanceSource`

### 🟢 小问题

4. **ResourceWarning 噪音**
   - mootdx config.json 未关文件句柄
   - baostock socket 未 logout

5. **STOKE_HOME 环境变量未持久化**

6. **macOS 无 timeout 命令**

---

## 五、港股美股专项测试（2026-06-27 15:52）

> 关不关梯子结果一样，底层全走境内源

| 维度 | 标的 | 结果 |
|:----|:----|:----:|
| 实时行情 - 港股 | 00700 腾讯 | ⚠️ 代码被映射为 `000700`，价格 5.x 元（实 400+） |
| 实时行情 - 美股 | AAPL 苹果 | ⚠️ 代码被映射为 `600839`（四川长虹），错标的 |
| 日线K线 - 港股 | 00700 腾讯 | ⚠️ 价格全错 |
| 日线K线 - 美股 | AAPL 苹果 | ❌ 空 DataFrame |
| 个股新闻 - 港股 | 00700 腾讯 | ✅ 正常 |
| 个股新闻 - 美股 | AAPL 苹果 | ✅ 正常 |
| 行业板块 | — | ❌ API 不存在 |
| 大盘情绪 | — | ❌ API 不存在 |

### 核心问题

1. **mootdx 只支持 A 股**：港股/美股代码被强行映射到 A 股代码池，数据全错
2. **多源 fallback 缺失**：mootdx 返回错误数据但不报错，后续源未触发
3. **API 命名不统一**：旧版 `intraday()`、`industry_board()`、`market_sentiment()` 在新版 Stoke 中不存在
4. **缓存脏数据**：空/错误 DataFrame 写入 SQLite，下次命中仍错

### 根因

- 路由层 `_route_data_type()` 以数据类型首字母判断归属源，**不验证返回有效性**
- mootdx TCP 将非 A 股代码强转 TDX 内部格式，产生假数据
- 应加**合理性校验**（价格范围、标的匹配），不合格则 fallback 到腾讯直连

### 改进建议

- 港股美股走腾讯直连源（`tencent_direct_source.py`）
- 增加数据质量校验层
- 暴露 `intraday`、`industry_board`、`market_sentiment` 等统一 API
- 缓存加 TTL，对空数据/错误数据不缓存或短 TTL

---

## 六、结论

**可用度：90/100**。6源中5源完美运行，核心功能（行情/K线/研报/估值/资金流）全部可用。唯一阻塞是财联社电报超时。

**A 股量化分析可立即使用**，港股美股暂不可用。
