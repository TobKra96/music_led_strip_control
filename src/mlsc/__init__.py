from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("music-led-strip-control")
except PackageNotFoundError:
    __version__ = "0+unknown"
