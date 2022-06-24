import re as _re
import copy as _copy
import os as _os
import math as _math
import threading as _threading

from . import geometry as _geometry


def debug(*msg):
  #print('DEBUG: '+' '.join([str(m) for m in msg]))
  pass


def shortenText(t, maxLength=30):
  t = _re.sub("\s+", " ", t.strip())
  if len(t) > maxLength:
    return t[:maxLength//2-2] + "..." + t[-maxLength//2-1:]
  return t


def testValidName(n):
  if _re.search("[^a-zA-Z0-9_]", n):
    raise ValueError("Names must only contain non alphanumeric characters and underscores: '"+n+"'")


def makeLiteral(val):
  if type(val) is float:
    return ['float', val]
  elif type(val) is int or (val - round(val))/val < 1e-6:
    return ['int', val]
  elif type(val) is list and len(val) == 2:
    return ['point', val]
  elif type(val) is str:
    return ['string', val]
  elif type(val) is geometry.Shape:
    return ['shape', val]
  else:
    raise ValueError("Invalid type for literal conversion: {} ('{}')".format(type(val), val))


class TypeCheck:
  def __init__(self, typesIn, returnType=None):
    if type(typesIn) is list:
      self._types = typesIn
    else:
      self._types = [typesIn]
    self._func = lambda x: x
    self._returnType = returnType

  def check(self, lit):
    return lit[0] in self._types

  def __call__(self, lit):
    if not self.check(lit):
      raise ValueError("Invalid type fed to function "
        +str(self._func)+", expected '"
        +(" or ".join(self._types))+"', found '"+lit[0]+"'.")
    if self._returnType == 'raw':
      return self._func(lit[1])
    elif self._returnType == None:
      return [lit[0], self._func(lit[1])]
    else:
      return [self._returnType, self._func(lit[1])]

  def __add__(self, func):
    self._func = func
    return self

  def __str__(self):
    return str(self._func)[:-1]+" (type safe)>"

  def __repr__(self):
    return str(self._func)[:-1]+" (type safe)>"


class Caller:
  def __init__(self, root, **dargs):
    self._root = root
    self._arglist = []
    self._letters = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']

    if 'start' in dargs and 'step' in dargs and 'stop' in dargs and len(dargs) == 3:
      if type(dargs['start']) is list:
        currentArglist = _copy.deepcopy(dargs['start'])
        while True:
          self._arglist.append(_copy.deepcopy(currentArglist))
          if not self._isNum(currentArglist[0][1]):
            currentArglist[0][1] = self._letters[int(_math.ceil(self._toNum(currentArglist[0][1]) + dargs['step'][0][1]))]
          else:
            currentArglist[0][1] += dargs['step'][0][1]
          dim = 0
          while True:
            if self._toNum(currentArglist[dim][1]) > self._toNum(dargs['stop'][dim][1]) or dargs['step'][dim][1] < 1e-5:
              currentArglist[dim][1] = dargs['start'][dim][1]
              dim += 1
              if dim < len(currentArglist):
                if not self._isNum(currentArglist[dim][1]):
                  currentArglist[dim][1] = self._letters[
                                    int(_math.ceil(self._toNum(currentArglist[dim][1]) + dargs['step'][dim][1]))]
                else:
                  currentArglist[dim][1] += dargs['step'][dim][1]
              else:
                break
            else:
              break

          if not dim < len(currentArglist):
            break
      else:
        currentArglist = [makeLiteral(dargs['start'])]
        while True:
          self._arglist.append(currentArglist)
          currentArglist = [[currentArglist[0][0], currentArglist[0][1] + dargs['step']]]
          if currentArglist[0][1] > dargs['stop']:
            break

    elif len(largs) > 0 or len(dargs) > 0:
      raise ValueError("Invalid arguments in parametric function call.")

  def _isNum(self, v):
    return type(v) is float or type(v) is int

  def _toNum(self, v):
    if type(v) is str and len(v) == 1 and v.lower() in self._letters:
      return self._letters.index(v.lower())
    else:
      return v


  def __call__(self, obj):
    if type(obj) is str:
      obj = self._root.shapeDict[obj]
    args = obj['args']
    union = _geometry.Shape()

    for argset in self._arglist:
      tree = _copy.deepcopy(obj['tree'])
      if len(argset) > len(args):
        raise ValueError("More sweep parameters than shape parameters.")
      tree.resolveNames({k: v for k, v in zip(args, argset)})

      if len(self._arglist[0]) == len(args):
        tree.evaluate()
        union.union(tree.getShape())
      else:
        raise ValueError("Unresolved names in parametric function call.")

    return ['shape', union]
