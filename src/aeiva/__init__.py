# src/aeiva/__init__.py
try:
    from importlib.metadata import version as package_version
except ImportError:
    # For Python<3.8 compatibility
    from importlib_metadata import version as package_version

try:
    __version__ = package_version("aeiva")
except PackageNotFoundError:
    __version__ = 'unknown'
