# polyp layout script

#-------------------------------------------------------------------
# pls import allows using shapes and symbols from external files.
# The AS keyword selects a namespace to prevent naming collisions,
# the default namespace is the scriptname without extension.
#
IMPORT lib.pls AS sub
IMPORT expensive.pls

#-------------------------------------------------------------------
# symbol and layer selection
#
SYMBOL primitives
LAYER 10

#-------------------------------------------------------------------
# primitive shapes (rect, polygon, text) and manipulations:
# translate, rotate, grow, round, array
# +, -  geometric addition, substration
# *     geometric intersection
#
rect(10) * rect(10).rotate(30)
+ polygon([0,0], [0,10],[10, 10])
      .translate(10, -5).rotate(15)
+ rect(5, se=[-5,5])
+ text('ABC', dy=5).translate(0, 10)

# acessing parametric shape from imported file
- sub.externalShape(5)
+ sub.externalShape(3)

# grow and round functions
+ text('DEF', dy=5, ne=[0, -8]).grow(-.1)
+ text('GHI', dy=5, nw=[2, -8]).grow(.1)
+ text('JKL', dy=5, nw=[10, -8]).round(.2)

# arrays
+ rect(1).rotate(45).array(5,15,.5,0).translate(25,0)


#-------------------------------------------------------------------
# Shapes are parametric shortcuts. Unlike symbols, shapes will not
# be referenced but hardcopied for each instance.
#
SHAPE cross(size, linewidth)
  rect(size, linewidth)
  + rect(linewidth, size)

SHAPE shiftedCross(size, linewidth, xOffset, yOffset)
  (rect(size, linewidth)
  + rect(linewidth, size)).translate(xOffset, yOffset)

# center and bounding box functions
SHAPE invertedRotatedCross(size, linewidth, margin)
  bb(cross(size, linewidth)).grow(margin)
  - cross(size, linewidth).rotate(45, center=center(cross(size, linewidth)))

#-------------------------------------------------------------------
# symbols can be referenced with the 'ref' command. Translating,
# rotating and array creation is also supported.
SYMBOL _main_
  ref(primitives).translate(20, 25).rotate(-12)


#-------------------------------------------------------------------
# Layer names can be used instead of numbers. Polyp will create a
# symbol called 'legend' that translates gds layer numbers to
# the pls layer names.
LAYER named_layer
  cross(10, 1)
  + invertedRotatedCross(15, 2, 2).translate(20, 0)


#-------------------------------------------------------------------
# SHAPEs have a call method, that allows them to be placed for a
# range of parameters. If step is step set to zero, only the start
# value of this parameter will be used.
LAYER param_sweeps
  shiftedCross.call(start=(5,.5,36,-10), step=(0,0,6,6), stop=(0,0,55,5))


#-------------------------------------------------------------------
# If expensive shapes are stored in external files, caching
# dramatically reduces the rendering time
#LAYER second_named_layer
#  expensive.hugeArray()


#-------------------------------------------------------------------
# Parametric symbols are also possible, each set of parameters will
# be rendered into a distinct symbol instance. The symbol name has
# to contain {} placeholders (see python format language) to create
# unique symbol names for all parameter sets used.
#
SYMBOL parametric_symbol_x{:02.0f}_y{:02.0f} (x, y)
LAYER another_named_layer
  text('x = '+int(x)+', y = '+int(y), dy=2, s=[0,0])
  + rect(dx=x, dy=y, n=[0, -1])

LAYER named_layer
  rect(dx=x, dy=y, n=[0, -1]).rotate(10)

LAYER 100 named_layer_with_fixed_number
  rect(dx=x, dy=y, n=[0, -1]).rotate(-10)


# The name passed to the 'ref' function is the parametric
# name with all placeholders replaced by empty strings.
#
SYMBOL _main_
  ref(parametric_symbol_x_y, 18, 1).translate( 0, -18)
  ref(parametric_symbol_x_y, 16, 2).translate(20, -18)
  ref(parametric_symbol_x_y, 14, 3).translate(40, -18)
