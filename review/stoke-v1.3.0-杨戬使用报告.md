# Stoke Skill v1.3.0 使用报告

> 日期：2026-06-27
> 安装来源：`~/Documents/stock-data/stoke-skill.zip`
> 安装目标：`~/.workbuddy/skills/stoke/` (SKILL.md) + `~/.agents/skills/stoke/` (Python包)
> 测试环境：macOS, Python 3.12, uv

---

## 一、安装过程摘要

| 步骤 | 操作 | 结果 |
|------|------|------|
| 解压到目标目录 | unzip | 成功 |
| uv sync | 自动构建 | **第一次失败** — 见问题 3 |
| 修复后 uv sync | 手动修复后重试 | **第二次失败** — 见问题 2 |
| 全面修复后 uv sync | 修复后重试 | 成功 |

安装过程共发现并修复 **2 个阻断性问题**，详见下文。

---

## 二、发现的问题

### P0 — 阻断性问题（必须修复才能正常使用）

#### 问题 1：stoke/calendar.py 与 Python stdlib calendar 模块命名冲突

**严重程度**：P0
**影响**：`uv sync` 构建失败，Python 进程无法启动

**现象**：
```
AttributeError: partially initialized module 'calendar' has no attribute 'day_abbr'
(most likely due to a circular import)
```

**原因**：`stoke/calendar.py` 在包构建时被放入 sys.path，优先级高于 Python 标准库的 `calendar` 模块。当 stdlib 的 `_strptime.py` 执行 `import calendar` 时，加载了 `stoke/calendar.py`，该文件又 `import pandas as pd`，pandas 初始化过程又回到 `import calendar`，形成循环引用。

**临时修复**：将 `stoke/calendar.py` 重命名为 `stoke/trading_calendar.py`，并更新 `store.py`、`sources/akshare_source.py`、`client_cached.py` 中的 import 路径。

**建议**：发布 v1.3.1 时将文件重命名，避免命名冲突。

---

#### 问题 2：pyproject.toml build-system.requires 缺少 pandas

**严重程度**：P0
**影响**：`uv sync` 构建失败

**现象**：
```
ModuleNotFoundError: No module named 'pandas'
hint: consider adding `pandas` to its `build-system.requires`
```

**原因**：`pyproject.toml` 的 `[build-system]` 只声明了 `setuptools`，但包构建过程（如 `calendar.py` → 现在修复后的 `trading_calendar.py`）在模块顶层导入了 `pandas`。

**临时修复**：在 `pyproject.toml` 中添加：
```toml
[build-system]
requires = ["setuptools", "pandas"]
```

**建议**：添加到 build-system.requires。

---

### P1 — 重要问题（影响功能或体验）

#### 问题 3：缓存数据库 schema 不兼容，strong_stocks 缓存永久失效

**严重程度**：P1
**影响**：每次调用 `strong_stocks()` 都触发缓存写入错误，自动降级为直连查询。数据能正常返回，但 cache 层完全失效。

**现象**：
```
sqlite3.IntegrityError: NOT NULL constraint failed: strong_stocks.symbol
pandas.errors.DatabaseError: Execution failed
```

**根因分析**：

`store.py` 第 255 行定义的 `strong_stocks` 表 schema 使用**中文列名**：
```sql
CREATE TABLE IF NOT EXISTS strong_stocks (
    date        TEXT NOT NULL,
    代码        TEXT NOT NULL,
    名称        TEXT,
    涨跌幅       REAL,
    入选理由      TEXT,
    所属行业      TEXT,
    fetched_at  TEXT NOT NULL,
    PRIMARY KEY (date, 代码)
);
```

但实际数据库中**已存在的旧表** schema 是混合的（旧版英文 + 新版中文拼接）：
```sql
-- 旧版字段
symbol TEXT NOT NULL,
name TEXT,
change_pct REAL,
reason TEXT,
industry TEXT,
-- 新版字段挂载在旧版后面
"代码" TEXT, "名称" TEXT, "涨跌幅" TEXT, ... "入选理由" TEXT, "所属行业" TEXT
```

旧表的 PRIMARY KEY 是 `(date, symbol)`，`symbol` 为 `NOT NULL`，但新代码写入时使用中文列名 `代码`，不填充 `symbol` 列，导致写入失败。

`CREATE TABLE IF NOT EXISTS` 语句在表已存在时**不修改**表结构，因此旧 schema 被永久保留。

**建议**：添加 schema 迁移逻辑。在 `store.py` 初始化时检测旧表结构，如果存在旧英文字段，自动 DROP + 重建，或使用 ALTER TABLE 兼容旧数据。

---

#### 问题 4：FallbackStoke 公共接口与 SKILL.md 文档不一致

**严重程度**：P1
**影响**：用户参考 SKILL.md 文档使用 `s.strong_stocks()` 等非代理方法时，行为不同于预期

**现状**：

| 文档声称 (SKILL.md) | FallbackStoke 实际暴露 | 访问方式 |
|-----|-----|-----|
| `s.strong_stocks()` | 否 | `__getattr__` 透传（无 fallback 保护） |
| `s.limit_up()` | 否 | `__getattr__` 透传（akshare guard） |
| `s.news("000001")` | 否 | `__getattr__` 透传 |
| `s.research("000001")` | 否 | `__getattr__` 透传 |
| `s.market_pb()` | 否 | `__getattr__` 透传 |
| `s.realtime_all()` | 否 | `__getattr__` 透传 |
| `s.kline_with_valuation()` | 否 | `__getattr__` 透传 |
| `s.realtime(...)` | 是 | 直接实现（4级 fallback） |
| `s.kline(...)` | 是 | 直接实现（4级 fallback） |
| `s.stock_list()` | 是 | 直接实现 |

`__getattr__` 透传的方法实际上调用的是 `StokeCached`（无 fallback 备份），用户在不知道的情况下会以为有多源备份。

**建议**：
- 方案 A：在 SKILL.md 中标注方法是否有多源备份
- 方案 B：让 `__getattr__` 也能感知 fallback（复杂）
- 方案 C：SKILL.md 中将 FallbackStoke 的方法列与实际一致

---

#### 问题 5：zip 包中残留根目录 calendar.py 文件

**严重程度**：P1
**影响**：解压后 `$STOKE_HOME/calendar.py` 文件直接处于项目根目录，同样会触发 stdlib 命名冲突

**现象**：
```
ls: .../stoke/stoke/calendar.py: No such file or directory
-rw-r--r--@ .../stoke/calendar.py    # 根目录还有一份
```

**原因**：zip 打包时可能包含了构建产物的残留文件。

**建议**：检查打包脚本，确保不将根目录的 `calendar.py` 打包进去。

---

### P2 — 次要问题

#### 问题 6：lxml 依赖被移除

旧版 `metadata.openclaw.install.uv` 中包含 `lxml`，新版移除了。

**影响**：`beautifulsoup4` 默认使用 `html.parser`，性能略低于 `lxml`。不影响功能，但旧版用户如果通过 git 更新可能遇到依赖不一致问题。

**建议**：如果确实不再需要，在 CHANGELOG 中注明。

---

#### 问题 7：ResourceWarning — mootdx socket 未正确关闭

每次初始化都会产生 `ResourceWarning`：
```
ResourceWarning: unclosed file <_io.TextIOWrapper name='/Users/zhaohongwei/.mootdx/config.json'>
ResourceWarning: unclosed <socket.socket ...>
```

**影响**：不影响功能，但在严格模式下会中断执行，且日志中产生噪音。

**建议**：在 `MootdxSource.__del__` 或上下文管理器中显式关闭连接。

---

#### 问题 8：FallbackStoke 缺少 probe() 方法

测试代码中调用 `s.probe()` 报 `AttributeError`。`probe_sources()` 函数存在于 `probe.py` 但未被暴露到 FallbackStoke 或 Stoke 的公开接口。

**影响**：开发者无法方便地检查数据源健康状态。

**建议**：在 FallbackStoke 中添加 `probe()` 方法。

---

#### 问题 9：没有测试套件

整个代码库没有单元测试或集成测试文件（`grep` 未发现 `test_`、`unittest`、`pytest` 相关引用）。

**影响**：问题 3（cache schema）如果有测试用例，在 CI 阶段就能发现。

**建议**：至少为 `store.py`（schema 变更）和 `fallback.py`（方法代理）添加基础测试。

---

## 三、功能验证

### 3.1 数据源探路

| 数据源 | 状态 | 备�� |
|--------|------|------|
| mootdx | 正常 | TCP 行情 |
| akshare | 正常 | 新闻/研报/信号 |
| baostock | 正常 | K线估值/财报 |
| efinance | 正常 | 资金流/龙虎榜 |
| legulegu | 正常 | PE/PB估值 |
| tencent_direct | 正常 | 实时行情 |

**6/6 源全部存活。**

### 3.2 核心方法测试

| 方法 | 结果 | 返回量 |
|------|------|--------|
| `strong_stocks('20260626')` | 通过 | 281 条 |
| `market_pb()` | 通过 | 5208 条 |
| `index_pe('上证50')` | 通过 | 5214 条 |
| `kline('000001')` | 通过 | 800 条 |

---

## 四、兼容性总结

### 与 v1.2.x 的主要差异

| 维度 | v1.2.x | v1.3.0 | 影响 |
|------|--------|--------|------|
| `calendar.py` | 存在 | 仍存在（命名冲突） | P0 |
| 缓存 DB schema | 英文列名 | 中文列名 | P1 |
| `lxml` 依赖 | 包含 | 移除 | P2 |
| `pyproject.toml` | 无需 pandas | 需要 pandas build dep | P0 |
| FallbackStoke 方法 | 7 个代理 | 7 个代理 + akshare guard | 无变化 |

### 对已有工作流的影响

- **`strong_stocks()` 功能正常**，只是缓存层失效。在当前的自动化投研任务中，每次调用都是实时查询，不影响结果
- **`market_pb()`/`index_pe()` 完全正常**
- **修复后 uv sync 可正常构建**

---

## 五、改进建议优先级

| 优先级 | 问题 | 建议 |
|--------|------|------|
| P0 | calendar.py 命名冲突 | 重命名为 trading_calendar.py，v1.3.1 发布 |
| P0 | build-system.requires | 添加 pandas |
| P1 | 缓存 DB schema 迁移 | 添加旧表检测 + DROP/CREATE 逻辑 |
| P1 | SKILL.md vs 实际 API 不一致 | 文档对齐实际实现 |
| P1 | zip 根目录残留文件 | 修复打包脚本 |
| P2 | ResourceWarning | 显式关闭 mootdx 连接 |
| P2 | 缺少 probe() 暴露 | FallbackStoke 添加 probe 方法 |
| P2 | 无测试套件 | 添加基础测试 |
| P2 | lxml 移除 | CHANGELOG 记录 |

---

## 六、结论

v1.3.0 功能上完整可用，6/6 数据源全通，核心查询方法正常返回数据。但存在 **2 个 P0 阻断性问题**导致安装失败，均已被本次报告中描述的临时修复方案解决。**建议发布 v1.3.1** 修复上述 P0 和 P1 问题后投入使用。

本次测试过程中发现并修复的问题已同步到两个安装位置（`~/.workbuddy/skills/stoke/` 和 `~/.agents/skills/stoke/`），当前环境下的 stoke v1.3.0 已可正常使用。

_报告生成：2026-06-27 10:42 CST | 杨戬 (WorkBuddy)_
