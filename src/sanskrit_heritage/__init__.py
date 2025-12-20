from .segmenter.interface import HeritageSegmenter
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("sanskrit-heritage")
except PackageNotFoundError:
    # Package is not installed (e.g., local dev without -e)
    __version__ = "unknown"

__all__ = ["HeritageSegmenter"]
