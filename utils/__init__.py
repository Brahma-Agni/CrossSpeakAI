"""
utils/__init__.py

Public surface of the utils sub-package.
"""

from utils.logger import get_logger
from utils.language_detector import LanguageDetector

__all__ = ["get_logger", "LanguageDetector"]
