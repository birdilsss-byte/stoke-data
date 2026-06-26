"""
EastmoneyPush2Source — 东财 push2 直连

数据源: push2.eastmoney.com (HTTP 公开 JSON API, 零鉴权)
覆盖: 行业板块排名 + 概念板块归属 + 全市场行情快照

设计原则:
  - 作为 akshare 的降级备胎，不替代 akshare
  - push2 是东财官方行情推送接口，稳定性远高于爬虫
  - 与 eastmoney/datacenter 共用全局限流 _em_rate_limit()
  - 零鉴权，仅需 Referer 头

参考: a-stock-data V3.2.3 §3.9 (行业板块排名) + §3.3 (概念板块)
"""

import json
import logging
import time
from typing import Optional

import pandas as pd
import requests

from stoke.config import RateLimiter
from stoke.config import RATE_LIMIT
from stoke.utils import retry_on_failure

logger = logging.getLogger(__name__)

# 复用 eastmoney_source 的全局限流
try:
    from stoke.sources.eastmoney_source import _em_rate_limit, EM_SESSION
except ImportError:
    # fallback: 独立限流
    EM_SESSION = requests.Session()
    EM_SESSION.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })
    EM_MIN_INTERVAL = 1.0
    _EM_LAST_CALL = [0.0]

    def _em_rate_limit():
        import random
        now = time.time()
        elapsed = now - _EM_LAST_CALL[0]
        if elapsed < EM_MIN_INTERVAL:
            time.sleep(EM_MIN_INTERVAL - elapsed + random.uniform(0, 0.3))
        _EM_LAST_CALL[0] = time.time()


# ==================== push2 API 常量 ====================

_PUSH2_CLIST = "https://push2.eastmoney.com/api/qt/clist/get"

# 行业板块: m:90+t:2 (东财行业分类, 零鉴权)
_SECTOR_FIELDS = (
    "f2,f3,f4,f12,f14,f104,f105,f128,f140"
)
_SECTOR_PARAMS = {
    "pn": "1",
    "pz": "200",
    "po": "1",
    "np": "1",
    "fltt": "2",
    "invt": "2",
    "fid": "f3",
    "fs": "m:90+t:2",
    "fields": _SECTOR_FIELDS,
}

# 概念板块: m:90+t:3
_CONCEPT_FIELDS = (
    "f2,f3,f4,f12,f14,f104,f128"
)
_CONCEPT_PARAMS = {
    "pn": "1",
    "pz": "500",
    "po": "1",
    "np": "1",
    "fltt": "2",
    "invt": "2",
    "fid": "f3",
    "fs": "m:90+t:3",
    "fields": _CONCEPT_FIELDS,
}

# push2 字段索引 (按 fields 参数顺序)
# f2=最新价, f3=涨跌幅(%), f4=涨跌额, f12=代码, f14=名称,
# f104=上涨家数, f105=下跌家数, f128=领涨股代码, f140=领涨股名称


class EastmoneyPush2Source:
    """东财 push2 直连 — 行业板块排名 + 概念板块，零鉴权"""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        interval = RATE_LIMIT.get("push2", 1.0)
        self.limiter = rate_limiter or RateLimiter(interval=interval, name="push2")
        self._session = EM_SESSION  # 共享东财族 Session
        logger.info("EastmoneyPush2Source 初始化，限流 %.1fs", self.limiter.interval)

    # ==================== 连通性检查 ====================

    def health_check(self) -> bool:
        """取行业板块排名第1页，验证连通性"""
        try:
            df = self.get_sector_rank()
            ok = not df.empty
            logger.info("push2 健康检查 %s", "通过" if ok else "失败")
            return ok
        except Exception as e:
            logger.warning("push2 健康检查失败: %s", e)
            return False

    # ==================== 行业板块排名 ====================

    @retry_on_failure(max_retries=2)
    def get_sector_rank(self) -> pd.DataFrame:
        """
        行业板块当日涨跌幅排名

        替代: akshare.get_sector_rank() 当 eastmoney 爬虫限流时

        注: push2 也走 eastmoney 基础设施，极端限流时可能同时不可用。
           但 push2 是官方 API（非爬虫），恢复通常比 akshare 快。

        Returns:
            DataFrame，列: sector_name, change_pct, up_count, down_count,
                           leader_code, leader_name, code
        """
        logger.info("push2 获取行业板块排名")

        self.limiter.wait()
        _em_rate_limit()

        try:
            r = self._session.get(
                _PUSH2_CLIST,
                params=_SECTOR_PARAMS,
                headers={
                    "Referer": "https://quote.eastmoney.com/",
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            logger.warning("push2 sector_rank 连接失败 (eastmoney 可能限流): %s", e)
            return pd.DataFrame()

        rows = data.get("data", {}).get("diff", [])
        if not rows:
            logger.warning("push2 sector_rank: data.diff 为空")
            return pd.DataFrame()

        # diff 是数组的数组，按 fields 顺序排列
        # fields: f2,f3,f4,f12,f14,f104,f105,f128,f140
        records = []
        for row in rows:
            try:
                records.append({
                    "sector_name": str(row[4]) if len(row) > 4 else "",
                    "change_pct": float(row[1]) if len(row) > 1 and row[1] != "-" else 0.0,
                    "up_count": int(row[5]) if len(row) > 5 and row[5] != "-" else 0,
                    "down_count": int(row[6]) if len(row) > 6 and row[6] != "-" else 0,
                    "leader_code": str(row[7]) if len(row) > 7 else "",
                    "leader_name": str(row[8]) if len(row) > 8 else "",
                    "code": str(row[3]) if len(row) > 3 else "",
                })
            except (ValueError, IndexError) as e:
                logger.debug("push2 行解析跳过: %s", e)
                continue

        df = pd.DataFrame(records)
        logger.info("push2 sector_rank: %d 个行业板块", len(df))
        return df

    # ==================== 概念板块排名 ====================

    @retry_on_failure(max_retries=2)
    def get_concept_rank(self) -> pd.DataFrame:
        """
        概念板块当日涨跌幅排名

        可用于替代 hot_keywords 的数据源——概念板块本身就是市场热搜的量化表达

        Returns:
            DataFrame，列: concept_name, change_pct, up_count, leader_code, code
        """
        logger.info("push2 获取概念板块排名")

        self.limiter.wait()
        _em_rate_limit()

        r = self._session.get(
            _PUSH2_CLIST,
            params=_CONCEPT_PARAMS,
            headers={
                "Referer": "https://quote.eastmoney.com/",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        rows = data.get("data", {}).get("diff", [])
        if not rows:
            logger.warning("push2 concept_rank: data.diff 为空")
            return pd.DataFrame()

        records = []
        for row in rows:
            try:
                records.append({
                    "concept_name": str(row[4]) if len(row) > 4 else "",
                    "change_pct": float(row[1]) if len(row) > 1 and row[1] != "-" else 0.0,
                    "up_count": int(row[5]) if len(row) > 5 and row[5] != "-" else 0,
                    "leader_code": str(row[6]) if len(row) > 6 else "",
                    "code": str(row[3]) if len(row) > 3 else "",
                })
            except (ValueError, IndexError) as e:
                logger.debug("push2 概念行解析跳过: %s", e)
                continue

        df = pd.DataFrame(records)
        logger.info("push2 concept_rank: %d 个概念板块", len(df))
        return df
