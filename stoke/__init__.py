"""
Stoke Data — A股量化投研数据层（精简版）

纯粹的数据获取层，无策略/时机/执行逻辑，可被其他模块或智能体复用。

12 大源，各司其职，零 API Key：
  mootdx (TCP)          — K线/实时行情/指数/板块，不限速
  akshare (HTTP)        — 新闻/研报/涨停/情绪/资金流/行业，5s限流
  baostock (HTTP)       — 复权K线/行业分类/财报/估值字段，1s限流
  efinance (HTTP)       — 极速K线/龙虎榜/股东数据/资金流，零限制
  legulegu (HTTP)       — PE/PB估值，直接 requests 无 akshare 依赖
  tencent_direct (HTTP) — 腾讯 qt.gtimg.cn 实时行情+K线，毫秒级
  eastmoney (HTTP)      — 东财研报（个股+行业+PDF），1.5s限流
  ths (HTTP)            — 同花顺一致预期EPS，1s限流
  datacenter (HTTP)     — 东财数据中心龙虎榜，1.5s限流
  cninfo (HTTP)         — 巨潮公告全文，1s限流
  push2 (HTTP)          — 东财 push2 直连行业/概念排名，零鉴权，akshare 降级备用
  ths_hot (HTTP)        — 同花顺热点直连强势股涨停/北向资金，零鉴权，akshare 降级备用

用法::
    from stoke import Stoke  # 默认带缓存
    s = Stoke()
    df = s.kline("000001")

    from stoke.fallback import FallbackStoke  # 带多源自动备份
    fs = FallbackStoke()
    df = fs.kline("000001")
"""

# 异常体系 — 必须在任何 import 之前，否则子模块加载时循环依赖
class StokeError(Exception): pass
class NetworkError(StokeError): pass
class DataEmptyError(StokeError): pass
class SourceNotReadyError(StokeError): pass

from stoke.client_cached import StokeCached as Stoke
from stoke.fallback import FallbackStoke

__version__ = "2.1.0"
__all__ = ["Stoke", "FallbackStoke", "StokeError", "NetworkError", "DataEmptyError", "SourceNotReadyError"]
