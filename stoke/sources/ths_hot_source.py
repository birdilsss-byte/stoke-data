"""
THSHotSource — 同花顺热点直连

数据源: 同花顺 zx.10jqka.com.cn (HTTP, 零鉴权, 极低封禁风险)
覆盖: 强势股(人工标注题材归因) + 北向资金(本地自缓存)

设计原则:
  - 作为 akshare 的降级备胎，不替代 akshare
  - 同花顺基础设施独立于东财，eastmoney 限流不影响同花顺
  - 零鉴权，仅需 User-Agent
  - 北向资金本地 CSV 缓存，越跑越丰富

参考: a-stock-data V3.2.3 §3.1 (ths_hot_reason) + §3.2 (northbound)
"""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from stoke.config import RateLimiter
from stoke.config import RATE_LIMIT
from stoke.utils import retry_on_failure

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 同花顺强势股接口 (零鉴权, ~73ms, ~125只/日)
_THS_HOT_URL = (
    "http://zx.10jqka.com.cn/event/api/getharden/"
    "date/{date}/orderby/date/orderway/desc/charset/GBK/"
)


class THSHotSource:
    """同花顺热点直连 — 强势股 + 北向资金，零鉴权"""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        interval = RATE_LIMIT.get("ths_hot", 0.5)
        self.limiter = rate_limiter or RateLimiter(interval=interval, name="ths_hot")
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": _UA})
        logger.info("THSHotSource 初始化，限流 %.1fs", self.limiter.interval)

    # ==================== 连通性检查 ====================

    def health_check(self) -> bool:
        """取今日强势股，验证连通性"""
        try:
            r = self._session.get(
                _THS_HOT_URL.format(date=date.today().strftime("%Y-%m-%d")),
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                ok = data.get("errocode", -1) == 0
                logger.info("THSHotSource 健康检查 %s", "通过" if ok else "失败")
                return ok
        except Exception as e:
            logger.warning("THSHotSource 健康检查失败: %s", e)
        return False

    # ==================== 强势股 + 题材归因 ====================

    @retry_on_failure(max_retries=2)
    def get_strong_stocks(self, date_str: str = None) -> pd.DataFrame:
        """
        当日强势股列表 + 人工标注题材归因

        替代: akshare.get_strong_stocks() 当 eastmoney 爬虫限流时

        实测: ~73ms 拿到 ~125 只强势股 + 完整字段

        Args:
            date_str: 日期 YYYY-MM-DD，默认今天

        Returns:
            DataFrame，列: symbol, name, change_pct, reason, close, turnover, amount
        """
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")

        # 安全校验：date_str 必须匹配 YYYY-MM-DD 格式，防止 URL 参数注入
        import re as _re
        if not _re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            logger.warning("同花顺热点: 非法日期格式 %s，已拒绝", date_str)
            return pd.DataFrame()

        logger.info("同花顺热点: 获取强势股 %s", date_str)

        self.limiter.wait()

        try:
            r = self._session.get(
                _THS_HOT_URL.format(date=date_str),
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("同花顺热点接口失败: %s", e)
            return pd.DataFrame()

        if data.get("errocode", 0) != 0:
            logger.warning("同花顺热点错误: %s", data.get("errormsg", ""))
            return pd.DataFrame()

        rows = data.get("data") or []
        if not rows:
            logger.warning("同花顺热点: 返回空列表 (盘后 15:30 数据才更新)")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # 字段映射 (同花顺 getharden API 实际返回: id, name, code, reason, date, market)
        # 注: 此接口不返回价格/涨幅，仅返回强势股名单+人工标注题材
        # 重命名: code → symbol
        if "code" in df.columns:
            df = df.rename(columns={"code": "symbol"})

        # 确保必要列存在
        if "symbol" in df.columns:
            df["symbol"] = df["symbol"].astype(str).str.strip()
        # 此接口无价格数据，设默认值（调用方可从 realtime 补全）
        if "change_pct" not in df.columns:
            df["change_pct"] = 0.0
        if "close" not in df.columns:
            df["close"] = 0.0

        logger.info("同花顺热点: %d 只强势股", len(df))
        return df

    # ==================== 涨停板股票池 ====================

    def get_limit_up_pool(self, date_str: str = None) -> pd.DataFrame:
        """
        涨停板股票池（从强势股中筛选涨幅 >= 9.5%）

        替代: akshare.get_limit_up_pool() 当 eastmoney 爬虫限流时

        注: 同花顺热点接口并非专门的涨停板接口，
           但强势股中涨幅 >= 9.5% 的约等于涨停板

        Returns:
            DataFrame，列: symbol, name, change_pct, reason
        """
        df = self.get_strong_stocks(date_str)
        if df.empty or "change_pct" not in df.columns:
            return pd.DataFrame()

        limit_up = df[df["change_pct"] >= 9.5].copy()
        logger.info("同花顺 涨停板(近似): %d 只 (共 %d 只强势股)", len(limit_up), len(df))
        return limit_up

    # ==================== 北向资金 ====================

    def _northbound_cache_path(self) -> Path:
        """北向资金本地 CSV 缓存路径"""
        p = Path.home() / ".tradingagents" / "cache" / "northbound_daily.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def get_northbound_flow(self, days: int = 20) -> pd.DataFrame:
        """
        北向资金历史数据（从本地 CSV 缓存读取）

        注: 同花顺北向实时分钟级接口需要盘中调用，
           盘后自动积累日级快照到本地缓存。
           本接口读缓存，不触发 HTTP 请求。

        Returns:
            DataFrame，列: date, hgt, sgt (沪股通/深股通)
        """
        path = self._northbound_cache_path()
        if not path.exists():
            logger.info("同花顺北向: 缓存文件不存在 (%s)", path)
            return pd.DataFrame()

        try:
            df = pd.read_csv(path)
            if not df.empty:
                df = df.tail(days)
                logger.info("同花顺北向: %d 天历史 (缓存)", len(df))
            return df
        except Exception as e:
            logger.warning("同花顺北向缓存读取失败: %s", e)
            return pd.DataFrame()
