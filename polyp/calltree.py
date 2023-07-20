import re as _re
import numpy as _np
import copy as _copy
import gdspy as _gdspy
import os as _os
import time as _time

from . import utils
from . import geometry

_PRINT_LIT_REDUCTION = False

class CallTree:
  _operators = [['make'], ['.'], ['^'], ['*', '/'], ['-', '+'],
                ['pstart', 'pend'], ['psep'], ['.'],
                ['oassign'], ['osep'], ['ostart', 'oend'],
                ['='], ['unpack'], [',']]

  def __init__(self, root, text=""):
    self._root = root
    self._children = []
    self._names = {}
    self._func = ""

    if text:
      nodeStack = [self, ]
      textbuffer = ""
      strDelimiter = ''
      for i, c in enumerate(text):
        if strDelimiter and c != strDelimiter:
          textbuffer += c

        elif strDelimiter and c == strDelimiter:
          textbuffer += c
          strDelimiter = ''

        elif c in ['"', "'"]:
          strDelimiter = c
          textbuffer += c

        elif c == "(":
          top = nodeStack[-1]
          new = CallTree(root)
          m = _re.search("[^a-zA-Z0-9_]", textbuffer[::-1])
          if m:
            new._func = textbuffer[len(textbuffer)-m.start():]
            top._addText(textbuffer[:len(textbuffer)-m.start()])
          else:
            new._func = textbuffer
          top._children.append(new)
          nodeStack.append(new)
          textbuffer = ""

        elif c == ")":
          nodeStack[-1]._addText(textbuffer)
          nodeStack.pop()
          textbuffer = ""

        else:
          textbuffer += c

        if len(nodeStack) == 0:
          raise ValueError("Additional ')' at:\n'"+utils.shortenText(text[i-30:i+30], maxLength=1e99)+"'")

      if len(nodeStack) > 1:
        raise ValueError("Additional '('.")

  def _addText(self, text):
    text = text.strip()
    if len(text) > 0:
      self._children.append(text.strip())

  def _py2lit(self, *vals):
    res = []
    def isInt(x):
      try: return _np.isclose(int(x), float(x))
      except KeyboardInterrupt: raise
      except: pass
    def isFloat(x):
      try: float(x); return True
      except KeyboardInterrupt: raise
      except: pass

    for val in vals:
      if type(val) is list and type(val[0]) is str:
        res.append(val)
      elif isInt(val):
        res.append(['int', int(val)])
      elif isFloat(val):
        res.append(['float', float(val)])
      elif type(val) is list and len(val) == 2:
        res.append(['point', val])
      elif type(val) is str:
        res.append(['string', val])
      elif isinstance(val, geometry.Shape):
        res.append(['shape', val])
      else:
        raise ValueError("Uknown variable type '"+str(type(val))+"'")
    if len(vals) == 1:
      return res[0]
    return res

  def createLiterals(self):
    for child in self._children:
      if type(child) is CallTree:
        child.createLiterals()

    #=====================================================================
    # generate literals from text
    i = 0
    inPoint = False
    while i < len(self._children):
      if type(self._children[i]) is str:
        i, inPoint = self._parseStr(i, inPoint)
      else:
        i += 1

    #=====================================================================
    # accumulate children
    i = 0
    while i < len(self._children)-1:
      if (hasattr(self._children[i], "_literals")
              and hasattr(self._children[i+1], "_literals")):
        self._children[i]._literals += self._children.pop(i+1)._literals
      else:
        i += 1


  def _instanciateShape(self, obj, largs, dargs):
    tree = obj['tree']
    argdict = {k: None for k in obj['args']}

    if len(largs) > len(argdict):
      raise ValueError(f'too many list args in parametric shape '
                       f'call: "{self._func}"')

    if len(argdict) > 0:
      for targetKey, listArg in zip(obj['args'], largs):
        argdict[targetKey] = self._py2lit(listArg)
      for key, val in dargs.items():

        # magic keyword arugument __ignore_extra_args__ is only passed
        # if unpacking operator was used
        if (key not in argdict
              and not '__ignore_extra_args__' in dargs.keys()):
          raise ValueError(f'passed named argument {key} which does not '
                           f'exist in shape\'s argument list')

        if key in argdict:
          if (argdict[key] is not None
              and not '__ignore_extra_args__' in dargs.keys()):
            raise ValueError("argument specified by list arg and named arg in parametric shape call: '{}'.".format(self._func))

          argdict[key] = self._py2lit(val)

      if None in argdict.values():
        raise ValueError("to few arguements in parametric shape call: '{}'.".format(self._func))
    unresolvedNames = tree.resolveNames(argdict)
    if unresolvedNames:
      raise ValueError("Unresolved names "
                      +", ".join(['"'+s+'"' for s in unresolvedNames])
                      +" in imported parameteric shape call: ".format(self._func))
    tree.evaluate(resolveGlobals=True)
    return tree.getShape()


  def evaluate(self, resolveGlobals=False):
    for child in self._children:
      if type(child) is CallTree:
        child.evaluate(resolveGlobals=resolveGlobals)

    #=====================================================================
    # accumulate children
    i = 0
    while i < len(self._children)-1:
      if (hasattr(self._children[i], "_literals")
              and hasattr(self._children[i+1], "_literals")):
        self._children[i]._literals += self._children.pop(i+1)._literals
      else:
        i += 1

    #=====================================================================
    # reduce literals

    if len(self._children) > 1:
      raise ValueError("Fatal error: children without literals not allowed.")

    self.resolveNames({}, resolveGlobals=resolveGlobals)
    self._reduceLiterals()

    #=====================================================================
    # prepare function parsing
    if self._func == "":
      if len(self._children) == 1:
        self._literals = [self._result]

    else:
      unresolvedNames = []
      largTypes = []
      largs = []
      dargTypes = {}
      dargs = {}

      # multiple arguments
      if self._result[0] == "argumentlist":
        for lit in self._result[1]:
          if lit[0] == 'assignment':
            if lit[1][1][0] == 'name':
              unresolvedNames.append(lit[1][1][1])
            dargs[lit[1][0]] = lit[1][1][1]
            dargTypes[lit[1][0]] = lit[1][1][0]
          else:
            if lit[0] == 'name':
              unresolvedNames.append(lit[1])
            largs.append(lit[1])
            largTypes.append(lit[0])

      # only one argument
      elif self._result[0] != 'none':
        if self._result[0] == 'name':
          unresolvedNames.append(self._result[1])
        largs = [self._result[1]]
        largTypes = [self._result[0]]
        dargs = {}

      def requireResolvedNamesOnly():
        if unresolvedNames:
          raise ValueError('Unresolved name(s): '
                           +', '.join(['"'+s+'"' for s in unresolvedNames])
                           +' in argumentlist of func "{}".'.format(self._func))

      if _PRINT_LIT_REDUCTION:
        utils.debug('Evaluate function "'+self._func+'", largs='
                    +str(largs)+', dargs='+str(dargs))

      #=====================================================================
      # rect function
      if self._func == "rect":
        requireResolvedNamesOnly()
        self._literals = [['shape', geometry.Rect(*largs, **dargs)]]

      #=====================================================================
      # polygon function
      elif self._func == "polygon":
        requireResolvedNamesOnly()
        self._literals = [['shape', geometry.Polygon(*largs, **dargs)]]

      #=====================================================================
      # text function
      elif self._func == "text":
        requireResolvedNamesOnly()
        self._literals = [['shape', geometry.Text(*largs, **dargs)]]

      #=====================================================================
      # qrcode function
      elif self._func == "qrcode":
        requireResolvedNamesOnly()
        self._literals = [['shape', geometry.Qrcode(*largs, **dargs)]]

      #=====================================================================
      # translate function
      elif self._func == "translate":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck(["shape", "point", "shaperef"])
                                  +geometry.Translator(*largs, **dargs)]]

      #=====================================================================
      # scale function
      elif self._func == "scale":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck(["shape",])
                                  +geometry.Scaler(*largs, **dargs)]]

      #=====================================================================
      # rotate function
      elif self._func == "rotate":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck(["shape", "point", "shaperef"])
                                  +geometry.Rotator(*largs, **dargs)]]

      #=====================================================================
      # mirror function
      elif self._func == "mirror":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck(["shape"])
                                  +geometry.Mirrower(*largs, **dargs)]]

      #=====================================================================
      # grow function
      elif self._func == "grow":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck("shape")
                                  +geometry.Grower(*largs, **dargs)]]

      #=====================================================================
      # smooth function
      elif self._func == "round":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck("shape")
                                  +geometry.Rounder(*largs, **dargs)]]

      #=====================================================================
      # create array of shapes
      elif self._func == "array":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck(["shape", "shaperef"])
                                  +geometry.Arrayer(*largs, **dargs)]]

      #=====================================================================
      # multiple calls to parametric shapes
      elif self._func == "call":
        requireResolvedNamesOnly()
        self._literals = [['func', utils.TypeCheck(['name', 'tree'], returnType='raw')
                                  +utils.Caller(self._root, *largs, **dargs)]]

      #=====================================================================
      # cast float to int
      elif self._func == "int":
        requireResolvedNamesOnly()
        if len(dargs) > 0 or len(largs) != 1:
          raise ValueError("Invalid arguments to 'int' call.")
        self._literals = [['int', int(largs[0])]]

      #=====================================================================
      # absolute value
      elif self._func == "abs":
        requireResolvedNamesOnly()
        if len(dargs) > 0 or len(largs) != 1:
          raise ValueError("Invalid arguments to 'abs' call.")
        self._literals = [['float', abs(largs[0])]]

      #=====================================================================
      # create letter from number
      elif self._func == "char":
        requireResolvedNamesOnly()
        letters = "abcdefghijklmnopqrstuvwxyz"
        if len(dargs) > 0 or len(largs) != 1 or largs[0] > len(letters):
          raise ValueError("Invalid arguments to 'char' call.")
        self._literals = [['string', letters[int(largs[0])]]]

      #=====================================================================
      # min/max/mean functions
      elif self._func in ["min", "max", "mean"]:
        requireResolvedNamesOnly()
        if len(dargs) > 0:
          raise ValueError("Function '"+self._func+"' does not support named arguments.")
        if len(largs) == 0:
          raise ValueError("Function '"+self._func+"' needs more than one argument.")
        try:
          largs = [float(f) for f in largs]
        except:
          raise ValueError("Function '"+self._func+"' supports only numerical inputs.")
        fdict = {"min": min, "max": max, "mean": lambda l: sum(l)/len(l)}
        self._literals = [['float', fdict[self._func](largs)]]

      #=====================================================================
      # square root
      elif self._func == "sqrt":
        requireResolvedNamesOnly()
        if len(dargs) > 0 or len(largs) != 1 or largs[0]<0:
          raise ValueError("Invalid arguments to 'sqrt' call.")
        self._literals = [['float', _np.sqrt(largs[0])]]

      #=====================================================================
      # trigonometric functions
      elif self._func in ["cos", "sin", "tan", "asin", "acos", "atan"]:
        requireResolvedNamesOnly()
        if len(largs) != 1 or any([a not in ['unit'] for a in dargs]):
          raise ValueError("Invalid arguments to 'cos' function.")
        u = dargs.get('unit', 'deg')
        if u == 'deg':
          largs[0] *= _np.pi/180
        elif u == 'rad':
          pass
        else:
          raise ValueError(f"Invalid value for 'unit' argument in "
                           f"'{self._func}' function.")
        if self._func == "sin":
          self._literals = [['float', _np.sin(largs[0])]]
        elif self._func == "cos":
          self._literals = [['float', _np.cos(largs[0])]]
        elif self._func == "tan":
          self._literals = [['float', _np.tan(largs[0])]]
        elif self._func == "asin":
          self._literals = [['float', 180/_np.pi*_np.arcsin(largs[0])]]
        elif self._func == "acos":
          self._literals = [['float', 180/_np.pi*_np.arccos(largs[0])]]
        else:
          self._literals = [['float', 180/_np.pi*_np.arctan(largs[0])]]

      #=====================================================================
      # arctan2
      elif self._func == "atan2":
        requireResolvedNamesOnly()
        if len(dargs) > 0 or len(largs) != 2:
          raise ValueError("Invalid arguments to 'abs' call.")
        self._literals = [['float', 180/_np.pi*_np.arctan2(largs[0], largs[1])]]

      #=====================================================================
      # calculate height of shape
      elif self._func == "height":
        requireResolvedNamesOnly()
        if len(largs) != 1:
          raise ValueError("Invalid arguments to 'height' function.")
        self._literals = [['float', largs[0].height()]]

      #=====================================================================
      # calculate width of shape
      elif self._func == "width":
        requireResolvedNamesOnly()
        if len(largs) != 1:
          raise ValueError("Invalid arguments to 'width' function.")
        self._literals = [['float', largs[0].width()]]

      #=====================================================================
      # calculate bounding box
      elif self._func == "bb":
        requireResolvedNamesOnly()
        if len(largs) != 1:
          raise ValueError("Invalid arguments to 'bb' function.")
        self._literals = [['shape', largs[0].boundingBox()]]

      #=====================================================================
      # calculate center of mass
      elif self._func == "center":
        requireResolvedNamesOnly()
        if len(largs) != 1:
          raise ValueError("Invalid arguments to 'center' function.")
        self._literals = [['point', largs[0].center()]]

      #=====================================================================
      # instanciate shapes
      elif self._func in self._root.shapeDict:
        requireResolvedNamesOnly()
        obj = _copy.deepcopy(self._root.shapeDict[self._func])
        shape = self._instanciateShape(obj, largs, dargs)
        utils.debug('self._literals = ["shape", '+str(shape)+']')
        self._literals = [['shape', shape]]

      #=====================================================================
      # look in imported database
      elif self._func in [name for lib in self._root.importDict.values()
                               for name in lib.shapeDict.keys()]:
        self._literals = [['import', self._func, [largs, dargs]]]

      #=====================================================================
      # create symbol reference:
      elif self._func == 'ref':
        if len(largs) == 1 and len(dargs) == 0:
          self._literals = [['shaperef',
                               _gdspy.CellReference(
                                    self._root.gdsLib.cells[largs[0]])]]
        elif len(largs) > 0 or len(dargs) > 0:
          for candidateName, candidate in self._root.paramSymDict.items():
            _cmp = lambda s: _re.sub(r'[\-_\{\}]+', '', s.lower())
            if _cmp(candidateName) == _cmp(largs[0]):
              utils.debug(f'matched {largs[0]} with {candidateName}')
              paramSym = candidate
              break
          else:
            raise ValueError('tried to create reference to undefined '
                             'parametric symbol "'+str(largs[0])+'" '
                             '(symbols may only be used after '
                             'their definition)')

          listParams = [list(v) for v in zip(largTypes[1:], largs[1:])]
          self._literals = [['paramshaperef', paramSym], ['operator', 'make'],
                            ['argumentlist',
                              listParams
                              +[['assignment', [k, self._py2lit(v)]]
                                    for k, v in dargs.items()]]]
        else:
          raise ValueError(f'ref requires one or more list args and zero or '
                           f'more named args, found {len(largs)} list args '
                           f'and {len(dargs)} named args')

      else:
        raise ValueError(f'invalid function/shape {self._func}')

      if _PRINT_LIT_REDUCTION:
        utils.debug('Evaluation result: ['+', '.join(['['+l[0]+', '
                        +utils.shortenText(str(l[1]), maxLength=10)+']' for l in self._literals])+']')


  def _parseStr(self, childId, inPoint=False):
    #=====================================================================
    # split string in literals 'str', 'int', 'float', 'name', 'operator'
    # and 'point'
    appliedChange = False
    s = self._children[childId]
    if not hasattr(self._children[childId], "_literals"):
      literals = []
      strDelimiter = ''
      buf = ''
      inNumber = False
      inName = False
      inObj = False
      s = s + ' '
      for prevC, c, nextC in zip(' ' + s[:-1], s, s[1:] + ' '):
        while True:
          reparseChar = False
          if strDelimiter:
            if c == strDelimiter:
              strDelimiter = ''
              literals.append(['string', buf])
            else:
              buf += c

          elif inNumber:
            if _re.match('[0-9.e]', c) or c in ['+', '-'] and prevC == 'e':
              buf += c
            else:
              n = float(buf)
              if n - round(n) < 1e-6 * n:
                literals.append(['int', n])
              else:
                literals.append(['float', n])
              inNumber = False
              reparseChar = True

          elif inName:
            if _re.match('[a-zA-Z0-9_]', c):
              buf += c
            else:
              utils.testValidName(buf)
              literals.append(['name', buf])
              inName = False
              reparseChar = True

          else:
            if c in ['"', "'"]:
              strDelimiter = c
              buf = ''

            elif c == '[':
              literals.append(['operator', 'pstart'])
              inPoint = True

            elif inPoint and c == ',':
              literals.append(['operator', 'psep'])

            elif c == ']':
              literals.append(['operator', 'pend'])
              inPoint = False

            elif inObj and c == '{':
              raise ValueError('objects cannot be nested')

            elif c == '{':
              literals.append(['operator', 'ostart'])
              inObj = True

            elif inObj and c == ',':
              literals.append(['operator', 'osep'])

            elif inObj and c == '=':
              literals.append(['operator', 'oassign'])

            elif c == '}':
              literals.append(['operator', 'oend'])
              inObj = False

            elif _re.match('[0-9]', c) or c == '.' and _re.match('[0-9]', nextC):
              reparseChar = True
              inNumber = True
              buf = ''

            elif c in [op for ops in self._operators for op in ops]:
              if c == '=' and literals[-1][0] == 'name':
                literals[-1][0] = 'assignname'
              literals.append(['operator', c])

            elif _re.match('[a-zA-Z_]', c):
              reparseChar = True
              inName = True
              buf = ''

            elif _re.match('\s', c):
              pass

            else:
              raise ValueError("Unexpected character '{}'".format(c))

          if not reparseChar:
            break

      self._children[childId] = CallTree(self._root)
      self._children[childId]._literals = literals

    return childId + 1, inPoint

  def _reduceLiterals(self):
    if hasattr(self, '_result'):
      return


    if _PRINT_LIT_REDUCTION:
      utils.debug("Start reducing:")
      utils.debug()

    if len(self._children) == 0:
      self._result = ['none', None]
      return

    literals = self._children[0]._literals
    for ops in self._operators:
      i = 0

      #=====================================================================
      # helper functions

      def popNextLit():
        if i < len(literals) - 1:
          return literals.pop(i+1)
        else:
          return None

      def popPrevLit():
        nonlocal i
        if i > 0:
          i -= 1
          return literals.pop(i)
        else:
          return None

      def viewNextLit():
        if i < len(literals) - 1:
          return literals[i+1]
        else:
          return None

      def viewPrevLit():
        if i > 0:
          return literals[i-1]
        else:
          return None

      def isNextLitType(types):
        if i < len(literals) - 1:
          lit = literals[i+1]
        else:
          return False
        if type(types) is list:
          return lit != None and lit[0] in types
        else:
          return lit != None and lit[0] == types

      def isPrevLitType(types):
        if i > 0:
          lit = literals[i-1]
        else:
          return False
        if type(types) is list:
          return lit[0] in types
        else:
          return lit[0] == types

      #=====================================================================
      # evaluate operators

      while i < len(literals):
        l = literals[i]

        if l[0] == 'tree':
          self.resolveNames({})

        elif l[0] == 'operator' and l[1] in ops:

          if _PRINT_LIT_REDUCTION:
            utils.debug(literals)

          #=====================================================================
          # two scalar numeric operands
          if (l[1] in ['^', '*', '/', '+', '-']
                  and isNextLitType(['float', 'int'])
                  and isPrevLitType(['float', 'int'])):

            op1 = popPrevLit()
            op2 = popNextLit()
            if l[1] == '^':
              if 'float' in [op1[0] or op2[0]] and op2[1] > 0:
                ty = 'float'
              else:
                ty = 'int'
              literals[i] = [ty, pow(op1[1], op2[1])]

            elif l[1] == '*':
              if 'float' in [op1[0] or op2[0]]:
                ty = 'float'
              else:
                ty = 'int'
              literals[i] = [ty, op1[1] * op2[1]]

            elif l[1] == '/':
              literals[i] = ['float', op1[1]/op2[1]]

            elif l[1] == '+':
              if 'float' in [op1[0] or op2[0]]:
                ty = 'float'
              else:
                ty = 'int'
              literals[i] = [ty, op1[1] + op2[1]]

            elif l[1] == '-':
              if 'float' in [op1[0] or op2[0]]:
                ty = 'float'
              else:
                ty = 'int'
              literals[i] = [ty, op1[1] - op2[1]]

          #=====================================================================
          # plus and minus for points
          elif (l[1] in ['+', '-'] and isNextLitType('point')
                                   and isPrevLitType('point')):
            op1 = popPrevLit()
            op2 = popNextLit()
            if l[1] == '+':
              literals[i] = ['point', [p1+p2 for p1,p2 in zip(op1,op2)]]
            elif l[1] == '-':
              literals[i] = ['point', [p1-p2 for p1,p2 in zip(op1,op2)]]

          #=====================================================================
          # plus operator for strings
          elif l[1] == '+' and (isNextLitType('string')
                            and not isPrevLitType('name')
                          or (isPrevLitType('string'))
                            and not isNextLitType('name')):
            op1 = popPrevLit()
            op2 = popNextLit()
            if op1[0] == 'int':
              op1[1] = str(int(op1[1]))
            else:
              op1[1] = str(op1[1])

            if op2[0] == 'int':
              op2[1] = str(int(op2[1]))
            else:
              op2[1] = str(op2[1])
            literals[i] = ['string', op1[1] + op2[1]]

          #=====================================================================
          # plus and minus as unary operators for numbers
          elif l[1] in ['+', '-'] and isNextLitType(['float', 'int']):
            op = popNextLit()
            if l[1] == '+':
              literals[i] = op
            elif l[1] == '-':
              literals[i] = [op[0], -op[1]]

          #=====================================================================
          # geometrical arithmetical operations
          elif(l[1] in ['+', '-', '*'] and isPrevLitType('shape')
                                       and isNextLitType('shape')):
            op1 = popPrevLit()
            op2 = popNextLit()
            if l[1] == '+':
              literals[i] = ['shape', op1[1].union(op2[1])]
            elif l[1] == '-':
              literals[i] = ['shape', op1[1].substract(op2[1])]
            elif l[1] == '*':
              literals[i] = ['shape', op1[1].intersect(op2[1])]

          #=====================================================================
          # point start, sep and end operators
          elif l[1] == 'pstart' and isNextLitType(['float', 'int']):
            op = popNextLit()
            literals[i] = ["point-x", op[1]]

          elif l[1] == 'psep' and isPrevLitType('point-x') and isNextLitType('point-y'):
            op1 = popPrevLit()
            op2 = popNextLit()
            literals[i] = ["point", (op1[1], op2[1])]

          elif l[1] == 'pend' and isPrevLitType(['float', 'int']):
            op = popPrevLit()
            literals[i] = ["point-y", op[1]]

          #=====================================================================
          # object start, sep and end operators
          elif (l[1] == 'oassign'
                  and isPrevLitType(['name'])):
            op1 = popPrevLit()
            op2 = popNextLit()
            literals[i] = ['obj', {op1[1]: op2}]

          elif l[1] == 'osep' and viewNextLit() == ['operator', 'oend']:
            op = popNextLit()
            literals[i] = op

          elif l[1] == 'osep' and viewPrevLit() == ['operator', 'ostart']:
            op = popPrevLit()
            literals[i] = op

          elif (l[1] == 'osep'
                  and isPrevLitType(['obj'])
                  and isNextLitType(['obj'])):
            op1 = popPrevLit()
            if op1[0] == 'obj':
              o1 = op1[1]
            else:
              o1 = {op1[1][0]: op1[1][1]}
            op2 = popNextLit()
            if op2[0] == 'obj':
              o2 = op2[1]
            else:
              o2 = {op2[1][0]: op2[1][1]}
            o1.update(o2)
            literals[i] = ['obj', o1]

          elif l[1] == 'ostart' and isNextLitType(['obj']):
            op = popNextLit()
            literals[i] = ['obj', op[1]]

          elif l[1] == 'oend' and isPrevLitType(['obj']):
            op = popPrevLit()
            literals[i] = ["obj", op[1]]

          #=====================================================================
          # dot operator for imported shapes
          elif(l[1] == '.' and isNextLitType('import')
                           and isPrevLitType('name')):
            op1 = popPrevLit()
            op2 = popNextLit()

            largs, dargs = op2[2]
            obj = _copy.deepcopy(
                          self._root.importDict[op1[1]].shapeDict[op2[1]])

            shape = self._instanciateShape(obj, largs, dargs)
            utils.debug('self._literals['+str(i)+'] = ["shape", '
                        ' '+str(shape)+']')
            literals[i] = ['shape', shape]

          #=====================================================================
          # dot operator for functions
          elif(l[1] == '.' and isNextLitType('func')
                           and (viewNextLit()[1].check(viewPrevLit())
                             or (isPrevLitType('operator')
                             and viewPrevLit()[1] in ['pend', 'point-y']))):
            if viewNextLit()[1].check(viewPrevLit()):
              op1 = popPrevLit()
              op2 = popNextLit()
              literals[i] = op2[1](op1)

          #=====================================================================
          # argument list operator
          elif l[1] == ',':
            op1 = popPrevLit()
            op2 = popNextLit()

            if op1 is None:
              l1 = []
            elif op1[0] == 'argumentlist':
              l1 = op1[1]
            else:
              l1 = [list(op1)]
            if op2 is None:
              l2 = []
            elif op2[0] == 'argumentlist':
              l2 = op2[1]
            else:
              l2 = [list(op2)]

            literals[i] = ['argumentlist', l1+l2]

          #=====================================================================
          # assignment operator
          elif l[1] == '=' and isPrevLitType(['name', 'assignname']):
            op1 = popPrevLit()
            op2 = popNextLit()
            literals[i] = ['assignment', [op1[1], op2]]

          #=====================================================================
          # make operator that creates shape refs
          elif (l[1] == 'make'
               and isPrevLitType('paramshaperef')
               and isNextLitType('argumentlist')):

            op1 = popPrevLit()
            op2 = popNextLit()

            paramSym = op1[1]
            pattern = paramSym[0]['name_pattern']

            # find out expected arguments
            for section in paramSym:
              argNames = section['args']
              break

            # check if all arguments are given
            usedParams = []
            dargs = {v[0]: v[1]
                          for k, v in op2[1] if k == 'assignment'}
            argdict = {}
            for k in argNames:
              if k in dargs:
                arg = dargs.pop(k)
              else:
                arg = op2[1].pop(0)
              if arg[0] == 'assignment':
                raise ValueError('did not pass enough args to '
                                 'parametric symbol')
              argdict[k] = arg
              usedParams.append(arg)

            # resolve names in used arguments
            _unresolvedNames = self.resolveNames({}, literals=usedParams,
                                                 resolveGlobals=True)
            if _unresolvedNames:
              raise ValueError(f'found unresolved names "'
                               f'{", ".join(_unresolvedNames)}" '
                               f'in argument list '
                               f'of parametric symbol {pattern}')

            # create symbol name
            def removeLitTypes(params):
              res = []
              for p in params:
                if p[0] == 'obj':
                  res.append('_'.join([f'{k}{v[1]}' for k, v in p[1].items()]))
                else:
                  res.append(p[1])
              return res

            # format and clean symbol name
            symInstanceName = (_re.sub(
                                    r'[^a-zA-Z0-9\._]+', ' ',
                                    pattern.format(
                                        *removeLitTypes(usedParams)))
                                  .strip().replace(' ', '_'))

            # check if different than pattern to validate that placeholders
            # existed in the original name
            if pattern == symInstanceName:
              raise ValueError(f'parametric symbol name {pattern} does not '
                                'seem to contain {} placeholders, please '
                               f'insert placeholders to guarantee unique '
                               f'symbol names for each parameter choice')

            if symInstanceName in self._root.gdsLib.cells.keys():
              sym = self._root.gdsLib.cells[symInstanceName]
            else:
              _gdspy.current_library = self._root.gdsLib
              sym = _gdspy.Cell(symInstanceName)
              self._root.gdsLib.add(sym)

            # if the newly added symbol is still empty, create geometry
            if len(list(sym)) == 0:
              for section in paramSym:
                tree = _copy.deepcopy(section['tree'])
                # replace root reference with true reference:
                tree._root = section['tree']._root

                layer = section['layer']
                argNames = section['args']
                unresolvedNames = tree.resolveNames(argdict)
                tree.evaluate(resolveGlobals=True)
                if tree._result[0] != 'none':
                  shapeResult = False
                  try:
                    s = tree.getShape()
                    shapeResult = True
                  except ValueError:
                    refs = tree.getShaperef()
                  if shapeResult:
                    if s is None:
                      if unresolvedNames:
                        raise ValueError('unresolved name(s) in layer shapes: '
                                              +', '.join(['"'+n+'"'
                                                  for n in unresolvedNames]))
                      else:
                        raise ValueError('unexpected None-shape found '
                                         'after instanciation '
                                         'of parametric symbol:\n'+str(tree))

                    shape = s._shape
                    if not shape is None:
                      if hasattr(shape, "layer"):
                        shape.layer = layer
                      elif hasattr(shape, "layers"):
                        shape.layers = [layer for _ in range(len(shape.layers))]
                      sym.add(shape)
                  else:
                    for ref in refs:
                      sym.add(ref)

              # add created sym to all parents
              # TODO: it would proably be better to use the 'importSymbols' of
              #       the PlsScript instance just before 'write_gds' is called.
              #       Otherwise layer transformation will not work, also the
              #       'parent' attriute is unnecessary, we have importDict
              #       already...
              parent = self._root.parent
              while parent is not None:
                _gdspy.current_library = parent.gdsLib
                if sym.name not in parent.gdsLib:
                  parent.gdsLib.add(sym)
                parent = parent.parent
              _gdspy.current_library = self._root.gdsLib

            literals[i] = ['shaperef', _gdspy.CellReference(sym)]


          #=====================================================================
          # if star is found and no left operand is found, replace with unpack
          # operator
          elif (l[1] == '*'
                and (viewPrevLit() is None
                  or isPrevLitType(['psep', 'osep'])
                  or viewPrevLit() == ['operator', ','])):
            literals[i] = ['operator', 'unpack']

          #=====================================================================
          # evaluate unpack operator
          elif l[1] == 'unpack' and isNextLitType(['obj']):
            op = popNextLit()
            arglist = [['assignment', [k, v]] for k, v in op[1].items()]

            # insert magic argument to silence errors on shape
            # instatiation
            arglist.append(['assignment', ['__ignore_extra_args__', ['none', None]]])

            literals[i] = ['argumentlist', arglist]

          else:
            if viewPrevLit():
              t1 = viewPrevLit()
            else:
              t1 = 'None'
            if viewNextLit():
              t2 = viewNextLit()
            else:
              t2 = 'None'

            if _PRINT_LIT_REDUCTION:
              utils.debug("parsing paused...")
              utils.debug()
            raise ValueError("Illegal operands for operator '{}': {} "
                             "and {}".format(l[1], t1, t2))

          if _PRINT_LIT_REDUCTION:
            utils.debug("applied operator:", l[1])
            utils.debug()

        i += 1

    if _PRINT_LIT_REDUCTION:
      utils.debug(literals)
      utils.debug("Done reducing.")
      utils.debug()

    if (len(self._children[0]._literals) > 1
            and not all([lit[0] == 'shaperef'
                  for lit in self._children[0]._literals])
            and not any([lit[0] == 'paramshaperef'
                  for lit in self._children[0]._literals])):
      raise ValueError(f'syntax error: expected expression to evaluate to '
                   f'one single toplevel object, found: "'
                   f'{", ".join([l[0] for l in self._children[0]._literals])}"'
                   f'did you forget to join shapes with +, - or'
                   f' * operators somewhere?')

    if (len(self._children[0]._literals) == 1
            and self._children[0]._literals[0][0] != 'shaperef'):
      self._result = self._children[0]._literals[0]
    else:
      self._result = self._children[0]._literals

  def resolveNames(self, names, resolveGlobals=False, literals=None):
    unresolvedNames = []

    #-----------------------------------------------------
    # prepare dict with all available names

    # magic names:
    names["__FILENAME__"] = ["string", _re.sub('\..*$', '',
                                       _os.path.basename(self._root.path))]
    names["__HASH__"] = ["string", self._root.hash]
    names["__DATE__"] = ["string", _time.strftime("%d.%m.%Y")]
    names["__TIME__"] = ["string", _time.strftime("%H:%M")]

    # constants:
    names["True"] = ['int', 1]
    names["False"] = ['int', 0]

    # add globals if enabled
    if resolveGlobals:
      for k in self._root.globals:
        if k not in names:
          names[k] = _copy.deepcopy(self._root.globals[k])

    #-----------------------------------------------------
    # resolve names from dict

    if literals is None:
      for child in self._children:
        if type(child) is CallTree:
          child.resolveNames(names)

    def resolveArglist(lit):
      unresolvedNames = []
      if lit[0] == 'argumentlist':
        for i, sublit in enumerate(lit[1]):
          if sublit[0] == 'assignment':
            unresolvedNames.extend(resolveArglist(sublit[1][1]))
          elif sublit[0] == 'name':
            unresolvedNames.extend(resolveArglist(sublit))
      elif lit[0] == 'name':
        if lit[1] in names:
          lit[0] = names[lit[1]][0]
          lit[1] = _copy.deepcopy(names[lit[1]][1])
        else:
          unresolvedNames.append(names)
      return unresolvedNames

    if hasattr(self, '_result'):
      unresolvedNames.extend(resolveArglist(self._result))

    if hasattr(self, '_literals') and literals is None:
      literals = self._literals

    if literals:
      for literal, nextLiteral in zip(literals,
                                      literals[1:]+[None]):
        if literal[0] == 'name':
          if literal[1] in names:
            literal[0] = names[literal[1]][0]
            literal[1] = _copy.deepcopy(names[literal[1]][1])
          else:
            unresolvedNames.append(literal[1])
        elif literal[0] == 'tree':
          unresolvedNames.extend(literal[1]['tree'].resolveNames(names))
          for name in names:
            if name in literal[1]['args']:
              literal[1]['args'].delete(name)
          if len(literal[1]['args']) == 0:
            literal[1]['tree'].evaluate()
            utils.debug('Replacing: '+str(literal[1]['tree'])+' -> ["shape", '
                                        +literal[1]['tree'].getShape()+ ']')
            literal[0] = 'shape'
            literal[1] = _copy.deepcopy(literal[1]['tree'].getShape())
        else:
          unresolvedNames.extend(resolveArglist(literal))
    return unresolvedNames


  def getShape(self, ref=False):
    utils.debug('getShape() called:')
    if hasattr(self, "_literals"):
      utils.debug('  > self._literals = '+str(self._literals))
    else:
      utils.debug('  > self._literals = <undefined>')
    if hasattr(self, "_result"):
      utils.debug('  > self._result = '+str(self._result))
    else:
      utils.debug('  > self._result = <undefined>')

    if hasattr(self, "_result"):
      if ref:
        if not all([r[0]=='shaperef' for r in self._result]):
          raise ValueError('expected only "shaperef" types but found: '
                            +str(self._result))
        return [r[1] for r in self._result]
      else:
        if self._result[0] != 'shape':
          raise ValueError('expected "shape" type result but found: '
                            +str(self._result))
        return self._result[1]
    return None

  def getShaperef(self):
    return self.getShape(ref=True)

  def __str__(self):
    return self._strRec()

  def __repr__(self):
    return self._strRec()

  def _strRec(self, level=0):
    if hasattr(self, "_literals"):
      hasLits = "'yes'"
    else:
      hasLits = "'no'"

    if hasattr(self, "_result"):
      hasRes = "'yes'"
    else:
      hasRes = "'no'"

    result = ("  "*level + "<CallTree object; func='"
                         + self._func+"'; literals? "
                         + hasLits+"; result? "
                         + hasRes+">\n")
    for child in self._children:
      if type(child) is str:
        result += "  "*(level+1) + "'" + _re.sub("\s+", " ", child.strip()) + "'\n"
      else:
        result += child._strRec(level+1)
    return result
