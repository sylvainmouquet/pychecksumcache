__version__ = "1.0.1"
__all__ = (
    "__version__",
    "PyChecksumCache",
)

from pychecksumcache.pychecksumcache import PyChecksumCache
import logging

logger = logging.getLogger("pychecksumcache")
logger.addHandler(logging.NullHandler())
