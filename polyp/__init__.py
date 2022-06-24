from . import plsscript
from . import plotting

# try to extract version info
try:
  import importlib.metadata
  __version__ = importlib.metadata.version('paperman')
except:
  try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution('paperman').version
  except:
    __version__ = '???'
