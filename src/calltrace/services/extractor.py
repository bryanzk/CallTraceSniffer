"""BlockSec extraction compatibility wrapper.

This module preserves the historical `BlockSecExtractor` import path while
routing implementation to the standalone `blocksec-parser` project.
"""

from __future__ import annotations

from .blocksec_adapter import get_playwright_extractor_class


_BaseExtractor = get_playwright_extractor_class()


class BlockSecExtractor(_BaseExtractor):
    """Backward-compatible alias of standalone parser extractor."""


__all__ = ["BlockSecExtractor"]
