"""POCArchitect AI Agent"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pocarchitect")
except PackageNotFoundError:
    __version__ = "0.3.0"  # fallback for development
