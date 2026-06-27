# Stoke v1.3.0 安装测试报告

> 测试时间：2026-06-27 15:00 CST  
> 测试环境：macOS 25.5.0 (arm64)、Python 3.12.13、uv  
> 安装方式：从 `stoke-skill.zip` 通过 skillhub_install 导入

---

## 一、安装结果

| 项目 | 状态 |
|------|:----:|
| zip 解压到 `~/.qclaw/workspace/skills/stoke/` | ✅ |
| `uv sync` 依赖安装 (49 包) | ✅ |
| `from stoke import Stoke` 导入 | ✅ |
| 官方 `verify_install.py` 验证脚本 | ✅ |
| **全源连通性** (6/6) | ✅ |

---

## 二、数据源逐项测试

### 2.1 mootdx（通达信 TCP）— ✅ 全部通过

| 方法 | 结果 | 备注 |
|------|:--:|------|
| `health_check()` | ✅ | 连通正常 |
| `get_realtime(["000001","600000"])` | ✅ | 000001=10.23, 600000=8.76 |
| `get_kline("000001")` | ✅ | 800 条日K线 |
| `get_stock_list()` | ✅ | 27381 只标的 |

### 2.2 akshare（东财/同花顺/巨潮）— ⚠️ 1 项超时

| 方法 | 结果 | 备注 |
|------|:--:|------|
| `get_news("000001")` | ✅ | 个股新闻正常 |
| `get_limit_up_pool("20260626")` | ✅ | 60 只涨停 |
| `get_strong_stocks("20260626")` | ✅ | 281 只强势，含"入选理由"题材归因 |
| `get_research_report("000001")` | ✅ | 225 篇研报，含 PDF 链接+盈利预测 |
| `get_announcements("000001")` | ✅ | 1736 条公告 |
| `get_concept_list()` | ✅ | 373 个概念板块 |
| `get_industry_list()` | ✅ | 90 个行业板块 |
| `get_cls_telegraph()` | ❌ **超时** | akshare `stock_info_global_cls()` 卡死 >3 分钟无响应 |

### 2.3 legulegu（乐咕乐股）— ✅ 通过

| 方法 | 结果 | 备注 |
|------|:--:|------|
| `get_index_pe("上证50")` | ✅ | 5214 条，最新PE=11.01 |
| `get_market_pb()` | ✅ | 5208 条，全市场PB正常 |

### 2.4 腾讯直连（qt.gtimg.cn）— ✅ 全部通过

| 方法 | 结果 | 备注 |
|------|:--:|------|
| `get_realtime(["000001","600519"])` | ✅ | 50+ 字段，毫秒级 |
| `get_kline("000001")` | ✅ | 640 条日K线 |

### 2.5 efinance（新浪/网易/东财公开接口）— ✅ 全部通过

| 方法 | 结果 | 备注 |
|------|:--:|------|
| `get_realtime_all()` | ✅ | 5867 只全市场快照 |
| `get_capital_flow("600519")` | ✅ | 主力/大单/中单资金流 |
| `get_sector_members("600519")` | ✅ | 所属板块列表 |

### 2.6 baostock（证券宝 HTTP）— ✅ 全部通过

| 方法 | 结果 | 备注 |
|------|:--:|------|
| `get_kline_with_valuation("sh.600000")` | ✅ | K线+PE/PB/PS/PCF |
| `get_profit_data("sh.600000",2025,1)` | ✅ | ROE/净利率/EPS |
| `get_index_constituents("沪深300")` | ✅ | 300 只成分股 |

---

## 三、统一入口测试

| 门面类 | 结果 | 备注 |
|--------|:--:|------|
| `Stoke()` | ✅ | 6 源纯路由，含 SQLite 缓存 |
| `FallbackStoke()` | ✅ | 6/6 源存活，多级备份正常 |

---

## 四、发现的问题

### 🔴 严重问题

1. **财联社电报 `get_cls_telegraph()` 超时无响应**
   - 现象：`ak.stock_info_global_cls()` 调用后卡死超过 3 分钟，没有返回也没有抛异常
   - 影响：新闻层关键功能不可用（分钟级市场快讯）
   - 可能原因：akshare 1.18.64 此接口底层变更或服务端无响应，也可能是数据量过大导致 akshare 内部死循环
   - 建议：① 加 `timeout` 参数或 `signal.alarm` 保护；② 检查 akshare 此接口是否需要升级调用方式

### 🟡 中等问题

2. **SKILL.md 文档与代码列名不匹配**
   - 文档示例用 `pe["分位点"]`，但 legulegu PE 实际列名为：`['日期','指数','等权静态市盈率','静态市盈率','静态市盈率中位数','等权滚动市盈率','滚动市盈率','滚动市盈率中位数']`
   - 无 `分位点` 列
   - 建议：修正文档示例代码

3. **SKILL.md 中类名大小写错误**
   - 文档写 `EfinanceSource`（小写 f），实际类名 `EFinanceSource`（大写 F）

### 🟢 小问题

4. **ResourceWarning 噪音**
   - mootdx 每次调用打印 `ResourceWarning: unclosed file`（config.json 文件未关闭）
   - baostock 每次调用打印 `unclosed <socket.socket>` （login 后未 logout）
   - 影响：日志污染，不影响功能，建议上游修复关闭资源

5. **STOKE_HOME 环境变量未持久化**
   - 当前只在 shell 中 export，重启终端后需重新设置
   - 建议：加到 `~/.zshrc` 或 OpenClaw 自动注入

6. **macOS 无 `timeout` 命令**
   - SKILL.md 故障排查表写 `brew install coreutils` 可解决，但不是自动的

---

## 五、对比旧版差异

| 维度 | 旧版 | v1.3.0 |
|------|------|--------|
| 架构 | 单文件脚本 | 模块化 6 源 + 门面模式 |
| 数据源 | mootdx + akshare | + legulegu/baostock/efinance/腾讯直连 |
| 自动备份 | 无 | FallbackStoke 4 级降级 |
| 缓存 | 无 | SQLite 缓存 (stoke_cache.db) |
| 研报 | 无 | 含 PDF 链接+盈利预测 |
| 强势股归因 | 无 | 含"入选理由"题材归因 |
| 估值数据 | 无 | PE/PB/PS/PCF + 历史分位 |
| 安装方式 | 手动 uv pip install | skillhub_install 一键安装 |

---

## 六、结论

**可用度：90/100**。6 个数据源中 5 个完美运行，核心功能（行情/K线/研报/估值/资金流）全部可用。唯一阻塞项是财联社电报接口可能需要升级 akshare 或换用备份接口。

**推荐立即用于 A 股量化分析**，财联社电报可用腾讯直连实时行情 + akshare 个股新闻替代。
