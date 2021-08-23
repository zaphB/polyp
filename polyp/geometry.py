import gdspy as _gdspy
import numpy as _np

from . import fonts

class Shape:
  def __init__(self, shape=None):
    self._shape = shape

  def union(self, operand):
    self._shape = _gdspy.fast_boolean(self._shape, operand._shape, 'or')
    return self

  def substract(self, operand):
    self._shape = _gdspy.fast_boolean(self._shape, operand._shape, 'not')
    return self

  def intersect(self, operand):
    self._shape = _gdspy.fast_boolean(self._shape, operand._shape, 'and')
    return self

  def translate(self, dx=None, dy=None, **args):
    if not self._shape is None:
      if dy is None:
        if type(dx) is not list:
          raise ValueError("Invalid arguments to translate function.")

        if dx is not None:
          if len(dx) == 2 and type(dx[1]) is not list:
            dx, dy = dx
          else:
            args[dx[0]] = dx[1][1]
            dx = None

        anchors = ['c', 'n','ne','e','se','s','sw','w','nw']
        for a in args:
          if a not in anchors:
            raise ValueError("Unexpected argument '{}' in rect call.".format(a))

        self._anchorType = None
        anchor = None
        for a in anchors:
          if a in args:
            if self._anchorType != None:
              raise ValueError("Multiple anchors in text definition.")
            self._anchorType = a
            anchor = args[a]

        if self._anchorType != None:
          if dx != None or dy != None:
            raise ValueError("No anchor definition allows in [dx,dy] style translation.")
          dx, dy = anchor

        bb = self.boundingBox()._getPointList()
        if self._anchorType == 'ne':
          self._shape.translate(-max(bb[0][0], bb[2][0]), -max(bb[0][1],bb[2][1]))
        elif self._anchorType == 'se':
          self._shape.translate(-max(bb[0][0], bb[2][0]), -min(bb[0][1],bb[2][1]))
        elif self._anchorType == 'sw':
          self._shape.translate(-min(bb[0][0], bb[2][0]), -min(bb[0][1],bb[2][1]))
        elif self._anchorType == 'nw':
          self._shape.translate(-min(bb[0][0], bb[2][0]), -max(bb[0][1],bb[2][1]))
        elif self._anchorType == 'n':
          self._shape.translate(-0.5*(bb[0][0]+bb[2][0]), -max(bb[0][1],bb[2][1]))
        elif self._anchorType == 'e':
          self._shape.translate(-max(bb[0][0], bb[2][0]), -0.5*(bb[0][1]+bb[2][1]))
        elif self._anchorType == 's':
          self._shape.translate(-0.5*(bb[0][0]+bb[2][0]), -min(bb[0][1],bb[2][1]))
        elif self._anchorType == 'w':
          self._shape.translate(-min(bb[0][0], bb[2][0]), -0.5*(bb[0][1]+bb[2][1]))
        elif self._anchorType == 'c':
          self._shape.translate(-0.5*(bb[0][0]+bb[2][0]), -0.5*(bb[0][1]+bb[2][1]))

      self._shape.translate(dx, dy)
    return self

  def rotate(self, angle, center=None):
    if not self._shape is None:
      if center != None:
        self._shape.rotate(angle, center)
      else:
        self._shape.rotate(angle, self.center())
    return self

  def mirror(self, p1, p2, copy=False):
    self._shape.mirror(p1, p2)
    return self

  def grow(self, size):
    if not self._shape is None:
      self._shape = _gdspy.offset(self._shape, size)
    return self

  def roundCorners(self, radius):
    if not self._shape is None:
      self._shape.fillet(radius)
    return self

  def _getPointList(self):
    if hasattr(self._shape, 'points'):
      return self._shape.points
    elif hasattr(self._shape, 'polygons'):
      return [point for poly in self._shape.polygons for point in poly]
    else:
      return []

  def height(self):
    ylist = [p[1] for p in self._getPointList()]
    if len(ylist) == 0:
      return 0
    else:
      return max(ylist) - min(ylist)

  def width(self):
    xlist = [p[0] for p in self._getPointList()]
    if len(xlist) == 0:
      return 0
    else:
      return max(xlist) - min(xlist)

  def boundingBox(self):
    P = self._getPointList()
    return Rect([min([p[0] for p in P]), min([p[1] for p in P])],
                [max([p[0] for p in P]), max([p[1] for p in P])])

  def center(self):
    P = self._getPointList()
    return [sum([p[0] for p in P])/len(P), sum([p[1] for p in P])/len(P)]

  def copy(self):
    return Shape(_gdspy.copy(self._shape, 0, 0))

  def __str__(self):
    return "<polyp.geometry.Shape: {} >".format(self._shape)

  def __repr__(self):
    return str(self)


class Rect(Shape):
  def __init__(self, p1=None, p2=None, **args):
    anchors = ['c', 'n','ne','e','se','s','sw','w','nw']
    for a in args:
      if a not in anchors + ['dx','dy']:
        raise ValueError("Unexpected argument '{}' in rect call.".format(a))

    if type(p1) is not list and type(p2) is not list:
      self._anchorType = None
      anchor = [0,0]
      for a in anchors:
        if a in args:
          if self._anchorType != None:
            raise ValueError("Multiple anchors in rectangle definition.")
          self._anchorType = a
          anchor = args[a]

      if self._anchorType == None:
        self._anchorType = 'c'

      if "dx" in args or "dy" in args:
        width = args['dx']
        height = args['dy']
      elif p1 is not None and p2 is not None:
        width = abs(p1)
        height = abs(p2)
      elif p1 is not None and p2 is None:
        width = abs(p1)
        height = abs(p1)
      else:
        raise ValueError("Anchor style rectangle definition must specify 'dx' and 'dy'.")

      if self._anchorType in ['ne','se','sw','nw']:
        p1 = anchor
        if self._anchorType == 'ne':
          p2 = (p1[0]-width, p1[1]-height)
        elif self._anchorType == 'se':
          p2 = (p1[0]-width, p1[1]+height)
        elif self._anchorType == 'sw':
          p2 = (p1[0]+width, p1[1]+height)
        elif self._anchorType == 'nw':
          p2 = (p1[0]+width, p1[1]-height)
      elif self._anchorType in ['n','e','s','w']:
        if self._anchorType == 'n':
          p1 = (anchor[0]+width/2, anchor[1])
          p2 = (p1[0]-width, p1[1]-height)
        elif self._anchorType == 'e':
          p1 = (anchor[0], anchor[1]+height/2)
          p2 = (p1[0]-width, p1[1]-height)
        elif self._anchorType == 's':
          p1 = (anchor[0]-width/2, anchor[1])
          p2 = (p1[0]+width, p1[1]+height)
        elif self._anchorType == 'w':
          p1 = (anchor[0], anchor[1]-height/2)
          p2 = (p1[0]+width, p1[1]+height)
      else:
        p1 = (anchor[0]-width/2, anchor[1]-height/2)
        p2 = (anchor[0]+width/2, anchor[1]+height/2)

    self._shape = _gdspy.Rectangle(p1, p2)


class Polygon(Shape):
  def __init__(self, *args):
    if any([type(a) is not tuple or len(a) != 2 for a in args]):
      raise ValueError("Unexpected argument passed to polygon constructor, expected point list: "+str(args))

    self._shape = _gdspy.Polygon(args)


class Text(Shape):
  def __init__(self, string, dy=None, **args):
    anchors = ['c', 'n','ne','e','se','s','sw','w','nw']
    for a in args:
      if a not in anchors + ['dx']:
        raise ValueError("Unexpected argument '{}' in rect call.".format(a))

    self._anchorType = None
    anchor = [0,0]
    for a in anchors:
      if a in args:
        if self._anchorType != None:
          raise ValueError("Multiple anchors in text definition.")
        self._anchorType = a
        anchor = args[a]

    if dy != None and 'dx' in args:
      raise ValueError("Can only specify text height (dy) or text width (dx).")

    if dy == None and not 'dx' in args:
      raise ValueError("Must specify text height (dy) or text width (dx).")

    if 'dx' in args:
      self._shape = _gdspy.PolygonSet(fonts.makeText(str(string), width=args['dx']))
    else:
      self._shape = _gdspy.PolygonSet(fonts.makeText(str(string), height=dy))

    bb = self.boundingBox()._getPointList()
    if 'dx' in args:
      top = max(bb[0][1],bb[2][1])
      bot = min(bb[0][1],bb[2][1])
    else:
      top = dy
      bot = 0

    if self._anchorType in ['ne','se','sw','nw']:
      if self._anchorType == 'ne':
        self.translate(-max(bb[0][0], bb[2][0]), -top)
      elif self._anchorType == 'se':
        self.translate(-max(bb[0][0], bb[2][0]), -bot)
      elif self._anchorType == 'sw':
        self.translate(-min(bb[0][0], bb[2][0]), -bot)
      elif self._anchorType == 'nw':
        self.translate(-min(bb[0][0], bb[2][0]), -top)
    elif self._anchorType in ['n','e','s','w']:
      if self._anchorType == 'n':
        self.translate(-0.5*(bb[0][0]+bb[2][0]), -top)
      elif self._anchorType == 'e':
        self.translate(-max(bb[0][0], bb[2][0]), -0.5*(bb[0][1]+bb[2][1]))
      elif self._anchorType == 's':
        self.translate(-0.5*(bb[0][0]+bb[2][0]), -bot)
      elif self._anchorType == 'w':
        self.translate(-min(bb[0][0], bb[2][0]), -0.5*(bb[0][1]+bb[2][1]))
    else:
      self.translate(-0.5*(bb[0][0]+bb[2][0]), -0.5*(bb[0][1]+bb[2][1]))
    self.translate(anchor[0],anchor[1])

class Rotator:
  def __init__(self, angle, center=None, unit="deg", copy=False):
    self._copy = copy
    if unit not in ['deg', 'rad']:
      raise ValueError("Unsupported angle unit: '"+unit+"', use 'deg' or 'rad'.")
    if unit == 'rad':
      self._angle = angle
    else:
      self._angle = _np.pi/180*angle
    self._center = center

  def __call__(self, op):
    if hasattr(op, 'rotate'):
      if self._copy:
        return op.copy().union(op.rotate(self._angle, self._center))
      else:
        return op.rotate(self._angle, self._center)

    elif hasattr(op, 'rotation'):
      if self._copy:
        raise ValueError('"copy" may only be specified when rotating shapes, not references.')
      if op.rotation == None:
        op.rotation = 0
      op.rotation += 180/_np.pi*self._angle
      return op

    else:
      if self._copy:
        raise ValueError('"copy" may only be specified when rotating shapes, not points.')
      c = self._center
      if not hasattr(c, '__len__') or len(c) != 2:
        c = [0,0]

      return ((op[0]-c[0])*_np.cos(self._angle) - (op[1]-c[1])*_np.sin(self._angle) + c[0],
              (op[0]-c[0])*_np.sin(self._angle) + (op[1]-c[1])*_np.cos(self._angle) + c[1])


class Mirrower:
  def __init__(self, p1=None, p2=None, x=None, y=None, copy=False):
    self._copy = copy
    if p1 is not None:
      self._p1 = p1
      self._p2 = p2
    elif x is not None and y is None:
      self._p1 = [x, 1]
      self._p2 = [x, -1]
    elif y is not None and x is None:
      self._p1 = [1, y]
      self._p2 = [-1, y]
    elif x is not None and y is not None:
      self._p1 = [x, y]
      self._p2 = None
    else:
      raise ValueError("Incomplete parameters to mirror: specify either one point, two "
                       +"points, named parameter x, named parameter y "
                       +"or named parameters x and y. Parameter 'copy' is optional")

  def __call__(self, op):
    if self._copy:
      if self._p2 is None:
        return op.copy().union(op.rotate(_np.pi, self._p1))
      else:
        return op.copy().union(op.mirror(self._p1, self._p2))
    else:
      if self._p2 is None:
        return op.rotate(_np.pi, self._p1)
      else:
        return op.mirror(self._p1, self._p2)

class Translator:
  def __init__(self, *largs, **dargs):
    self._largs = largs
    self._dargs = dargs

  def __call__(self, op):
    if hasattr(op, 'translate'):
      if self._dargs.get('copy', False):
        return op.copy().union(op.translate(*self._largs, **self._dargs))
      else:
        return op.translate(*self._largs, **self._dargs)
    elif len(self._largs) == 2 and len(self._dargs) == 0:
      self._dx = self._largs[0]
      self._dy = self._largs[1]
    elif (len(self._largs) == 0
          and len(self._dargs) == 2
          and 'dx' in self._dargs
          and 'dy' in self._dargs):
      self._dx = self._dargs['dx']
      self._dy = self._dargs['dy']
    else:
      raise ValueError("Invalid translator instanciation.")
    if 'copy' in dargs:
      raise ValueError('"copy" may only be specified when translating shapes.')
    return (op[0]+self._dx, op[1]+self._dy)

class Grower:
  def __init__(self, d):
    self._d = d

  def __call__(self, op):
    return op.grow(self._d)


class Rounder:
  def __init__(self, r):
    self._r = r

  def __call__(self, op):
    return op.roundCorners(self._r)

class Arrayer:
  def __init__(self, lx, ly, dx=0, dy=0):
    if lx <= 0 or ly <= 0:
      raise ValueError("Zero or negative sized array not possible.")
    self._lx = lx
    self._ly = ly
    self._dx = dx
    self._dy = dy

  def __call__(self, op):
    lx = self._lx
    ly = self._ly
    dx = self._dx
    dy = self._dy
    if type(op) is _gdspy.CellReference:
      bb = op.ref_cell.get_bounding_box()
      if bb is not None:
        w = abs(bb[1][0] - bb[0][0])
        h = abs(bb[1][1] - bb[0][1])
      else:
        w = 0
        h = 0
      return _gdspy.CellArray(op.ref_cell, int(lx), int(ly), (dx+w, dy+h), op.origin, op.rotation)
    else:
      result = Shape()
      w = op.width()
      h = op.height()
      op.translate(-((lx-1) * (w + dx))/2,
                  -((ly-1) * (h + dy))/2)

      for y in range(int(ly)):
        for x in range(int(lx)):
          result.union(op)
          op.translate(w + dx, 0)
        op.translate(-(w + dx)*lx, h + dy)

      return result
