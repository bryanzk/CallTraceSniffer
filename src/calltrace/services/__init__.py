"""
业务逻辑服务模块
"""
try:
    from .extractor import BlockSecExtractor
except Exception:  # Optional dependency (playwright) may be unavailable in tests.
    BlockSecExtractor = None

__all__ = ['BlockSecExtractor']
