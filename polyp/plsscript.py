import re as _re
import gdspy as _gdspy
import os as _os
import time as _time
import hashlib as _hashlib
import collections as _collections
import threading as _threading
import matplotlib.pyplot as _plt
import pickle as _pickle
import copy as _copy

from . import utils
from . import calltree
from . import geometry
from . import plotting

class PlsScript:
  def __init__(self, text='', forceRerender=False, parent=None):
    self.path = ''
    self._cachedPath = ''
    self.parent = parent

    if hasattr(text, 'read'):
      self.path = _os.path.abspath(text.name)
      _text = ''
      for line in text:
        if not _re.match("\s*#", line):
          _text += line + "\n"
      text = _text

    def getCachedPath(path):
      if not path:
        return ''
      filename = '.'.join(self.path.split('/')[-1].split('.')[:-1])
      basedir = '/'.join(self.path.split('/')[:-1])
      return basedir+'/.'+filename+'.plb'

    def isPathCached(path, newerThan=0):
      if forceRerender:
        return False
      cachedPath = getCachedPath(path)
      return (_os.path.exists(cachedPath)
          and _os.path.getmtime(path) < _os.path.getmtime(cachedPath)
          and newerThan < _os.path.getmtime(cachedPath))

    def recursiveDependencyCheck(dependencies, newerThan=0):
      newest = max([newerThan] + [_os.path.getmtime(p) for p in dependencies.keys()])
      if not all([isPathCached(p, newerThan=newest) for p in dependencies.keys()]):
        return False
      return all([len(sub) == 0 or recursiveDependencyCheck(sub, newerThan=newest)
                      for sub in dependencies.values()])

    self._cachedPath = getCachedPath(self.path)

    renderFile = True
    if isPathCached(self.path):
      utils.debug('loading '+_os.path.basename(self._cachedPath)+' from cache')
      try:
        self.__dict__ = _pickle.load(open(self._cachedPath, 'rb'))
        def fixRefs(script):
          for sec in script.sections:
            sec._root = script
            def fixTreeRefs(tree):
              tree._root = script
              for child in tree._children:
                fixTreeRefs(child)
            fixTreeRefs(sec._callTree)
          for subscript in script.importDict.values():
            fixRefs(subscript)
        fixRefs(self)

        if recursiveDependencyCheck(self._dependencies):
          renderFile = False
        else:
          utils.debug('at least one dependency is outdated, rerendering...')

      except:
        utils.debug('loading failed.')

    if renderFile:
      if self.path:
        utils.debug('rendering '+_os.path.basename(self.path))
      self.sections = []
      self.shapeDict = {}
      self.paramSymDict = {}
      self.importDict = {}
      self.layerDict = {}
      self._dependencies = {}
      self.gdsLib = _gdspy.GdsLibrary(unit=1e-6, precision=1e-10)
      _gdspy.current_library = self.gdsLib

      # split into sections:
      pos = 0
      lastHead = ""
      lastSection = None
      while True:
        # update hash value
        self.hash = str(int(sum([b*256**i
                                  for i, b in enumerate(
                                        _hashlib.sha1((_re.sub("\s+", "", text)
                                                          +"".join([s.hash for s in self.importDict.values()]))
                                                      .encode()).digest())]
                        ) % 1e5)).rjust(5,'0')

        m = _re.compile("(SHAPE|SYMBOL|LAYER|IMPORT).*\n").search(text, pos)
        if not m:
          break
        if lastHead != "":
          newSection = _ScriptSection(self, lastHead, text[pos:m.start()], lastSection, forceRerender)
          self.sections.append(newSection)
          lastSection = newSection

        lastHead = text[m.start():m.end()]
        pos = m.end()

      if lastHead != "":
        self.sections.append(_ScriptSection(self, lastHead, text[pos:], lastSection, forceRerender))

      # add legend in case of named layers
      if any([name != None for name in self.layerDict.values()]):
        _gdspy.current_library = self.gdsLib
        if 'legend' in self.gdsLib.cells:
          self.gdsLib.cells.pop('legend')

        legendSym = _gdspy.Cell('legend')
        self.gdsLib.add(legendSym)

        legendShape = geometry.Shape()
        for text in [str(num)+': '+str(name) for num, name in sorted(self.layerDict.items())]:
          legendShape.translate(0, 10).union(geometry.Text(text, dy=8, w=[0, 0]))
        legendShape._shape.layers = [255 for _ in range(len(legendShape._shape.layers))]
        legendSym.add(legendShape._shape)

      if self._cachedPath:
        _pickle.dump(self.__dict__, open(self._cachedPath, 'wb'))


  def lookupLayerNum(self, layerName, default=None):
    for num, name in self.layerDict.items():
      if layerName == name:
        return num
    if default is not None:
      i = default
    else:
      i = 0
      while i < 1e3:
        if i not in self.layerDict.keys():
          break
        i += 1
    self.layerDict[i] = layerName
    return i


  def _sortLibrary(self):
    self.gdsLib.cells = _collections.OrderedDict([(k, v)
                for k, v in sorted(self.gdsLib.cells.items())])


  def writeResults(self, path, pdfWidth=12, pdfTitle=None, pdfGrid=False):
    _gdspy.current_library = self.gdsLib
    self._sortLibrary()
    if path.endswith(".gds"):
      _gdspy.current_library = self.gdsLib
      self.gdsLib.write_gds(path)

    elif path.endswith(".pdf"):
      baseName = path[:-4]
      for symName, symbol in self.gdsLib.cells.items():
        if len(self.gdsLib.cells.keys()) > 1:
          ext = "/"+symName
        else:
          ext = ""

        bb = symbol.get_bounding_box()
        w = bb[1][0] - bb[0][0]
        h = bb[1][1] - bb[0][1]
        pdfFigsize = (pdfWidth+2, pdfWidth*h/w+2)

        _plt.figure(figsize=pdfFigsize)
        if not pdfTitle is None:
          _plt.title(pdfTitle)
        _plt.grid(pdfGrid)
        plotting.plot(self.gdsLib.cells, symName)
        _plt.xlabel("X [$\mu$m]")
        _plt.ylabel("Y [$\mu$m]")
        _plt.legend()
        dirs = _os.path.dirname(baseName+ext+".pdf")
        if dirs != '':
          _os.makedirs(dirs, exist_ok=True)
        _plt.savefig(baseName+ext+".pdf")
        _plt.close()
    else:
      raise ValueError("Unknown file extension: '*.{}'".format(path.split('.')[-1]))


  def importSymbols(self, lib, layerMap={}):
    libDuplicate = _copy.deepcopy(lib)
    for layerFrom, layerTo in layerMap.items():
      for cell, origCell in zip(libDuplicate.cells.values(), lib.cells.values()):
        if hasattr(cell, 'elements'):
          for elem, origElem in zip(cell.elements, origCell.elements):
            for i in range(len(elem.layers)):
              if origElem.layers[i] == layerFrom:
                elem.layers[i] = layerTo
    _gdspy.current_library = self.gdsLib
    for symName in libDuplicate.cells:
      try:
        libDuplicate.extract(symName)
      except:
        pass


  def openViewer(self, currentLibMtl=None):
    _gdspy.current_library = self.gdsLib
    self._sortLibrary()
    if currentLibMtl is None:
      currentLibMtl = [_gdspy.current_library, False]

    viewer = _gdspy.LayoutViewer.__new__(_gdspy.LayoutViewer)

    def watchLib():
      nonlocal viewer
      lastLib = currentLibMtl[0]
      while not hasattr(viewer, 'canvas'):
        _time.sleep(.1)
      viewer.bind_all('<KeyPress-q>', lambda e: viewer.quit())
      while(True):
        if currentLibMtl[0] != lastLib:
          lastLib = currentLibMtl[0]
          viewer.cells = lastLib.cells
          viewer._update_canvas()
        _time.sleep(.5)
        if currentLibMtl[1]:
          break

    self._thr = _threading.Thread(target=watchLib)
    self._thr.start()
    try:
      viewer.__init__()
    except:
      raise

    currentLibMtl[1] = True
    self._thr.join()

  def __str__(self):
    return "\n".join(str(s) for s in self.sections)


class _ScriptSection:
  def __init__(self, root, head, text, prevSection, forceRerender=False):
    self._root = root
    self._head = head.strip()
    self._text = text.strip()
    self._prev = prevSection
    self._symbol = None
    self._layer = None

    #=====================================================================
    # parse header

    head = _re.split("\s+", self._head)
    self._isParametricSymbol = None
    self._cleanName = None
    self._symNamePattern = None
    self._args = None

    if head[0] == "IMPORT":
      if len(head) != 2 and (len(head) != 4 or head[2] != "AS"):
        raise ValueError("Invalid IMPORT statement: '"+self._head+"'")
      self._importFile = head[1]
      if len(head) > 3:
        self._namespace = head[3]
      else:
        self._namespace = "_".join(head[1].split("/")[-1].split(".")[:-1])
      utils.testValidName(self._namespace)

      importPath = _os.path.join(_os.path.dirname(root.path), self._importFile)
      suffix = importPath.split(".")[-1]

      if suffix == 'pls':
        script = PlsScript(open(importPath, 'r'),
                           forceRerender=forceRerender,
                           parent=root)
        root._dependencies[importPath] = script._dependencies
        root.importDict[self._namespace] = script

        # convert layers
        layerMap = {}
        for num, name in script.layerDict.items():
          if name is not None:
            lookedupNum = self._root.lookupLayerNum(name, default=num)
            if lookedupNum != num:
              layerMap[num] = lookedupNum

        self._root.importSymbols(script.gdsLib, layerMap)
        for name, sym in script.paramSymDict.items():
          if name in self._root.paramSymDict.keys():
            raise ValueError("Duplicate parametric symbol name "+str(name))
          self._root.paramSymDict[name] = sym
      else:
        raise ValueError('Unsupported import file format "'+suffix+'"')

    elif head[0] == "SHAPE":
      m = _re.match("([^()]+)\(([^()]*)\)", " ".join(head[1:]))
      if not m:
        raise ValueError("Invalid SHAPE statement: '"+self._head+"'")
      self._shapeName = m.group(1).strip()
      self._args = [a.strip() for a in m.group(2).split(",")]
      try:
        self._args.remove('')
      except ValueError:
        pass
      for n in self._args + [self._shapeName]:
        utils.testValidName(n)

    elif head[0] == "SYMBOL":
      symName = ' '.join(head[1:])
      if (symName.count('(') == 0
          and symName.count(')') == 0):
        utils.testValidName(symName)
        self._isParametricSymbol = False
        self._symbol = symName

      elif (symName.count('(') == 1
          and symName.count(')') == 1
          and symName.find('(') < symName.find(')')
          and symName.strip()[-1] == ')'):

        symNamePattern, args = symName.strip()[:-1].split('(')
        symNamePattern = symNamePattern.strip()
        args = [a.strip() for a in args.split(',')]
        for arg in args:
          utils.testValidName(arg)

        cleanName = ''
        skip = False
        for c in symNamePattern:
          if c == '{':
            skip = True
          if not skip:
            cleanName += c
          if c == '}':
            skip = False
        utils.testValidName(cleanName)

        if len(args) > 0:
          self._isParametricSymbol = True
          self._symbol = None
          self._cleanName = cleanName
          self._symNamePattern = symNamePattern
          self._args = args
        else:
          self._isParametricSymbol = False
          self._symbol = symPatternName

      else:
        raise ValueError("Invalid SYMBOL statement: '"+self._head+"'")

    elif head[0] == "LAYER":
      if len(head) < 2 or len(head) > 3:
        raise ValueError("Invalid LAYER statement: '"+self._head+"'")
      elif len(head) == 3:
        layerNum = int(head[1])
        layerName = head[2].strip()
      else:
        try:
          layerNum = int(head[1])
          layerName = None
        except:
          layerName = head[1].strip()
          layerNum = None

      if layerName is not None:
        utils.testValidName(layerName)
        lookedupNum = root.lookupLayerNum(layerName, default=layerNum)
        if layerNum is not None and layerNum != lookedupNum:
          raise ValueError(("Layer number conflict: wanted to assign layer '{}' to "
                           +"number {}, but LUT entry is {}.")
                              .format(layerName, layerNum, lookedupNum))
        layerNum = lookedupNum

      else:
        if layerNum not in root.layerDict:
          root.layerDict[layerNum] = None

      if layerNum < 0 or layerNum > 255:
        raise ValueError("Layer number {} exceeds 0...255 range.".format(layerNum))
      self._layer = layerNum

    else:
      raise ValueError("Invalid keyword.")

    #=====================================================================
    # reverse seek for layer/symbol/parametric symbol context
    prev = self._prev
    while self._symbol == None or self._layer == None or not self._isParametricSymbol:
      if not prev:
        break
      if self._isParametricSymbol == None and prev._isParametricSymbol != None:
        self._isParametricSymbol = prev._isParametricSymbol
      if self._cleanName == None and prev._cleanName != None:
        self._cleanName = prev._cleanName
      if self._symNamePattern == None and prev._symNamePattern != None:
        self._symNamePattern = prev._symNamePattern
      if self._args == None and prev._args != None:
        self._args = prev._args
      if self._symbol == None and prev._symbol != None:
        self._symbol = prev._symbol
      if self._layer == None and prev._layer != None:
        self._layer = prev._layer
      prev = prev._prev

    #=====================================================================
    # parse section text into calltree
    self._callTree = calltree.CallTree(root, self._text)
    self._callTree.createLiterals()

    try:
      self._callTree.evaluate()
    except Exception as e:
      if head[0] != "SHAPE" and not self._isParametricSymbol:
        raise e

    # shape
    if head[0] == "SHAPE":
      root.shapeDict[self._shapeName] = {"args": self._args,
                                         "tree": self._callTree}

    # parametric symbol
    elif self._isParametricSymbol:
      if self._cleanName not in root.paramSymDict.keys():
        root.paramSymDict[self._cleanName] = []
      root.paramSymDict[self._cleanName].append(
                                {"name_pattern": self._symNamePattern,
                                 "args": self._args,
                                 "tree": self._callTree,
                                 "layer": self._layer})

    # if array of shaperef instances
    elif (len(self._callTree._result) > 0
              and all([type(res) is list
                       and len(res) == 2
                       and res[0] == 'shaperef'
                            for res in self._callTree._result])):
      if not self._symbol:
        raise ValueError('Shaperefs found without symbol context')
      if self._symbol in root.gdsLib.cells:
        sym = root.gdsLib.cells[self._symbol]
      else:
        sym = _gdspy.Cell(self._symbol)
        root.gdsLib.add(sym)
      for ref in self._callTree._result:
        sym.add(ref[1])

    # if shape instance
    elif len(self._callTree._result) == 2 and self._callTree._result[0] == 'shape':
      if not self._symbol or type(self._layer) is not int:
        raise ValueError('Shapes found without symbol or layer context')
      if self._symbol in root.gdsLib.cells:
        sym = root.gdsLib.cells[self._symbol]
      else:
        sym = _gdspy.Cell(self._symbol)
        root.gdsLib.add(sym)

      s = self._callTree.getShape()
      if s is None:
        raise ValueError("Unresolved names in layer shapes.")

      shape = s._shape
      if not shape is None:
        if hasattr(shape, "layer"):
          shape.layer = self._layer
        elif hasattr(shape, "layers"):
          shape.layers = [self._layer for _ in range(len(shape.layers))]
        sym.add(shape)


  def __str__(self):
    return ("<_ScriptSection object; head='{}', text='{}'>".format(utils.shortenText(self._head),
                                                                   utils.shortenText(self._text))
            +"\n"+str(self._callTree))
