"""
Stoke 全局配置
"""

import logging
import sys
import time
import random
import warnings

# 抑制第三方库的 ResourceWarning（mootdx 裸 open、baostock 未关闭 socket）
warnings.filterwarnings("ignore", category=ResourceWarning, module="mootdx")
warnings.filterwarnings("ignore", category=ResourceWarning, module="baostock")
warnings.filterwarnings("ignore", category=ResourceWarning, module="socketutil")

# 限流间隔（秒）
RATE_LIMIT = {
    "mootdx": 0.0,          # TCP 协议，不限流
    "akshare": 5.0,         # 东财系，必须 3-5 秒
    "legulegu": 1.0,        # 乐咕乐股 HTTP，1 秒即可
    "baostock": 1.0,        # 证券宝 HTTP，稳定 1 秒即可
    "efinance": 0.5,        # 整合多源，无官方限制，0.5 秒即可
    "tencent_direct": 0.3,  # 腾讯 qt.gtimg.cn，毫秒级响应，0.3 秒即可
    "eastmoney": 1.5,       # 东财研报，≥1.5s 防封
    "ths": 1.0,             # 同花顺一致预期，1 秒即可
    "datacenter": 1.5,      # 东财数据中心，≥1.5s 防封
    "cninfo": 1.0,          # 巨潮公告，1 秒即可
    "push2": 1.0,           # 东财 push2 直连，1s 防风控
    "ths_hot": 0.5,         # 同花顺热点直连，0.5s
}

# 跨实例共享限流状态 — 同一个 name 的 RateLimiter 跨实例协调
_GLOBAL_LAST: dict = {}


class RateLimiter:
    """请求频率控制，带随机抖动。同进程内跨实例共享状态。多 Agent 建议错峰调度。"""
    def __init__(self, interval: float = 5.0, name: str = ""):
        self.interval = interval
        self._key = name

    def wait(self):
        if self.interval <= 0:
            return
        now = time.time()
        last = _GLOBAL_LAST.get(self._key, 0.0)
        elapsed = now - last
        if elapsed < self.interval:
            sleep = self.interval - elapsed
            jitter = random.uniform(-0.3, 0.3) * min(sleep, 1.0)
            time.sleep(max(0.0, sleep + jitter))
        _GLOBAL_LAST[self._key] = time.time()


def setup_logging(level: str = "INFO", log_file: str = ""):
    """
    配置全局日志

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)，默认 INFO
        log_file: 日志文件路径，空字符串表示仅输出到 stderr
    """
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )

    for noisy in [
        "mootdx", "tdxpy", "akshare", "urllib3",
        "requests", "charset_normalizer", "matplotlib",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("pandas.io.sql").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成 (级别=%s)", level.upper())
