"""
core/__init__.py

Exposes the top-level public surface of the core package.
"""

from core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
