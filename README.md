# Polyp will not be continued

This is just a note that no further development in this project is to be expected. Mainly because 1) the underlying [gdspy](https://github.com/heitzmann/gdspy) is no longer maintained since it became [gdstk](https://github.com/heitzmann/gdstk) and 2) because the [gdsfactory](https://github.com/gdsfactory/gdsfactory) project has implemented anything I ever dreamed to do with polyp on a way more solid footing than polyp. 


# Human-Readble-Ascii to gdsII Converter

Polyp is a renderer that creates gdsII layout files from an all-ascii human-readable layout language. Geometric shapes are constructed from primitive shapes, e.g., squares, circles or text, that are translated, rotated, scaled or otherwise transformed and can be added, subtracted or intersected with each other.

Polyp is definitely interesting for you if you
* are not afraid of using the command line
* have experience with drawing gdsII files
* are a fan of mark-up languages

Polyp is probably not for you if you
* prefer manually drawing geometry
* feel uncomfortable using the command line

A minimal example is shown in the following:

```
SYMBOL main
  LAYER 0
    rect(10).rotate(45) - text("hello world", dy=3)
```

If this is saved in a text file `minimal.pls` it can be compile with the command

```
polyp minimal.pls
```

This creates a gdsII file `minimal.gds` containing a single symbol with the name `main` that contains a shape in layer 0. This shape is given by a square with side length 10, rotated by 45 degrees, from which the text 'hello world' with height 3 is cut-out. For more advanced examples see the examples section of this readme.


# Installation

Install polyp and its dependencies with

```
pip install polyp
```

Executing `polyp -h` on the shell should now show the polyp quick help, `polyp --version` should show the expected version number.


# Basic usage

To compile a .pls polyp layout script to a .gds file, run `polyp filename`, where `filename` has to be replaced with the path of the .pls file.

Passing the `-v` (`--view`) option (`polyp -v filename`) compiles the layout script and opens a simple viewer afterwards.

Passing the `-w` (`--watch`) option keeps checking the .pls file for updates, re-compiles in case a change in the file is detected and keeps the compiled result open in a viewer.

If the `-p` (`--pdf`) option is passed to polyp, the layout script is compiled to .pdf instead of .gds. One pdf file is created for each gdsII symbol.


# Examples

This list of examples starts from a minimal .pls example and moves to more and more complex layout scripts step by step. A formal documentation of the polyp layout language is currently not available, feel free to contact me or open an issue in case this is needed.


## Minimal example

A minimal layout script example looks like this:

```
SYMBOL main
  LAYER 0
    rect(10)
```

The capitalized `SYMBOL` and `LAYER` context keywords have to be placed in the beginning of a line and mark the beginning of a symbol or layer context. Note that the indentation used in these examples is not required for the scripts to compile successfully, but improves readability.

The last line `rect(10)` of this example creates a geometric shape, namely a 10x10 square. Since the `rect` is placed inside the `SYMBOL` and `LAYER` contexts, it will be placed in the gdsII symbol named `main` and in layer `0` in the resulting .gds file. Create a text file with the above content, name it `test.pls`, compile it with `polyp -v text.pls`, and see for yourself!


## Using different layers and symbol names

The following example shows how geometry can be added to different layers and symbols:

```
SYMBOL main
  LAYER 1
    rect(10)
  LAYER 2
    polygon([0,0], [0,10], [-5,5])

SYMBOL sub
  LAYER 1
    rect(5, 10)
```

The line `rect(10)` again creates a 10x10 square in symbol main, layer 1. The `polygon(...)` built-in creates a polygon using the passed list of coordinates. Coordinates are specified as a comma separated pair of numbers enclosed in square brackets `[...]` in polyp layout scripts. The `polygon(...)` line is placed after `LAYER 2`, hence the resulting polygon is placed in layer 2 of the gds file.

The line `SYMBOL sub` then switches the active symbol from `main` to `sub`, hence all following geometry is placed in the symbol `sub`. In this case, the last line `rect(5, 10)` creates a rectangle of 5 units width and 10 units height.


## Creating text

The built-in `text(...)` creates geometry defined by a string of characters. The named parameter `dx` or `dy` must be present to specify the resulting text's height or width. For example `text("hello world", dy=10)` creates a geometry reading "hello world" with a height of 10 units.

The text is placed with the shape's center of mass placed at [0,0] by default. Optionally, an anchor position can be specified by passing a named parameter `n`, `e`, `s`, `w`, `ne`, `se`, `sw`, or `nw`, which places the text such that the respective side or corner of the bounding box is placed at the given position. For example the line `text("hello world", se=[0,0])` places the lower left corner of the text geometry on the point [0,0].


## Other ways to call `rect(...)`

We already saw that calling rect with a single parameter creates a square with the respective side length. It is also possible to pass two numeric parameters, e.g. `rect(5, 10)`, to create a rectangle with the given width and height. In addition, an anchor position can be specified by passing a named argument `n`, `e`, `s`, `w`, `ne`, `se`, `sw`, or `nw`, analogous to `text(...)`.


## Geometric sum, difference and intersect operations

In polyp layout scripts, geometric objects can be easily added, subtracted or intersected with each other using the arithmetic operators `+`, `-` and `*`, respectively:

```
SYMBOL main
  LAYER 1
    rect(10) + polygon([0,0], [0,10], [-5,5])
  LAYER 2
    rect(10) - polygon([0,0], [0,10], [-5,5])
  LAYER 3
    rect(10) * polygon([0,0], [0,10], [-5,5])
```

In this example, the sum of the square and the polygon is placed in layer 1, the difference is placed in layer 2, and the intersection of both is placed in layer 3.


## Translate, rotate, mirror, grow, round, array

Every geometric shape supports a number of transformations that can be invoked by appending a `.` and the respective transformation:

### Translate

To shift a shape to another position, use `.translate(...)`:

*Relative shift:* The code line `rect(10).translate(20, 30)` creates a square with side length 10 and shifts it 20 units in x-direction and 30 units in y-direction

*Absolute shift:* The code line `rect(10).translate(s=[10,20])` creates a square with side length 10 and shifts it such that the southern end of the shape is moved to the coordinate `[10, 20]`. Here, south refers to the lower middle of the shapes bounding box. All possible anchors are `n`, `e`, `s`, `w`, `ne`, `se`, `sw` and `nw`, referring to the respective corner of side of the shapes bounding box.

Translate supports the optional boolean arguement `copy`, which if set to true, causes the untranslated shape to be kept in the result, e.g. `rect(10).translate(0, 20, copy=True)`.


### Rotate

To rotate a square by 30 degrees, use `rect(10).rotate(30)`. Optionally, the center of rotation can be specified as a second parameter: `rect(10).rotate(30, [0, 10])`. By default, the center of rotation is given by the center of mass of the rotated geometry.

Rotate supports the optional boolean argument `copy`, which if set to true, causes the unrotated shape to be kept in the result, e.g. `rect(10).rotate(120, copy=True)`.


### Scale

To scale a shape, use `.scale(s1, s2, center)`, where `s1` is the scale factor in x-direction, `s2` is the scale factor in y-direction and `center` is the reference point of the scaling. If `center` is omitted, the center of mass of the shape is used. If `s2` is omitted, both directions will be scaled by `s1`.

Scale supports the optional boolean argument `copy`, which if set to true, causes the unscaled shape to be kept in the result, e.g. `rect(10).scale(3, center=[0,0], copy=True)`.


### Mirror

To mirror a geometry at a given point or line, use the `.mirror(...)`. The following example shows three different ways of calling the method:

```
SYMBOL main
  LAYER 1
    polygon([0,0], [0,10], [10,0]).mirror([-5, 5], copy=True)
  LAYER 2
    polygon([0,0], [0,10], [10,0]).mirror(x=-5, copy=True)
  LAYER 3
    polygon([0,0], [0,10], [10,0]).mirror([5,10], [10,0], copy=True)
```


*Mirror at a given point:* Passing a single coordinate to the mirror method performs a point-reflection of the shape at the given coordinate.

*Mirror at the x or y-axis:* Passing a named parameter x or y, e.g., `x=-5`, `y=10`, mirrors with respect to the implied line.

*Mirror at a freely defined line:* Passing two coordinates to mirror causes the shape to be mirrored at the line that connects these to points.

Mirror supports the optional boolean arguement `copy`, which if set to true, causes the unmirrored shape to be kept in the result, e.g. `rect(10).mirror([20, 5], copy=True)`.

### Grow/shrink

To grow or shrink a given geometry, use `.grow(...)`. Grow expects a single numeric parameter that specifies by how many units to grow the respective shape in all directions. If this number is negative, the shape is shrunk instead.

### Round corners

To round all corners a given geometry, use `.round(...)`. Round expects a single numeric parameter that specifies the maximum radius of the corners after rounding.

### Creating arrays of shapes

To place a shape many times in as a 1D or 2D array, use `.array(...)`. Array expects two numeric parameters that specify how often the shape should be multiplied in x and in y-direction. Two more optional parameters can be used to specify column and row spacing. The default spacing is zero, implying that the shape is repeated in x- or y-direction with a period equal to its width or height, respectively.

This example code places an array of rotated squares with and without specified column and row spacing:

```
SYMBOL main
  LAYER 1
    rect(10).rotate(45).array(5, 5)
  LAYER 2
    rect(10).rotate(45).array(5, 5, 10, 20)
```

### Calculating height, width, bounding box and center of mass

The functions `height(...)` and `width(...)` return the height and width of the shape that is passed as an argument. For example `height(rect(10))` returns 10. The function `bb(...)` returns the bounding box of a shape. The function `center(...)` returns a shapes center of mass.


### Math

The trigonometric functions and there inverse functions are available as `cos`, `sin`, `tan`, `asin`, `acos`, `atan`. Angles are given in units of degrees. The function `atan2` is a variant of `atan` that uses two arguments and is able to handle the full circle. See the numpy documentation of `atan2` for further details.

The function `abs(...)` returns the absolute value of the passed number, `sqrt(...)` returns the square root. The functions `min`, `max` and `mean` return the minimum, maximum or arithmetical mean of the passed list of numbers.


### Type conversions

Use `int(...)` to convert a number to integer. Use `char(...)` to convert an integer number to the respective letter of the alphabet.


## Defining (parametric) shapes

Drawing large geometries using only primitive shapes results in large expressions that get increasingly confusing and difficult to read. To make expressions more readable, polyp allows to define named shapes with the keyword `SHAPE`:

```
SHAPE diamond()
  rect(10).rotate(45)

SYMBOL main
  LAYER 1
    diamond()
  LAYER 2
    diamond().grow(-2).round(1)
  LAYER 3
    diamond().translate(5, 5)
  LAYER 3
    diamond() - text('A', dy=5)
```

Like the `SYMBOL` and `LAYER` keywords, `SHAPE` must be upper case and placed at the beginning of a line. `SHAPE` is followed by the desired symbol name and a pair of round brackets. The following lines specify the desired geometry. In this example, the shape name is `diamond` and the geometry is given by a square rotated by 45 degrees. Later, in the layers of the symbol `main`, this shape is created using the statement `diamond()`. As shown, all available methods to manipulate geometry can also be applied to `diamond()`.

**Important:** it is not possible to use gdsII references for `SHAPE`s in polyp. `SHAPE`s are always copied as often as they are used in the geometry. It is also not possible to use multiple layers in a `SHAPE`. If you want reference the same piece of geometry multiple times in your script to save memory, or if you want to define multi layered geometries, you are looking for the gdsII symbol and symbol references, which are described later in this tutorial.

It is often desirable to define shapes that use free parameters. In polyp, this can be done by specifying an argument list in the brackets of the `SHAPE` definition:

```
SHAPE label(string, height)
  rect(width(text(string, dy=height))+3, height+1)
    - text(string, dy=height)

SYMBOL main
  LAYER 1
    label("such a nice label", 10)
```

In this example, the parametric shape `label` expects two parameters. The resulting geometry consists of a rectangle with the width calculated from the width of a text instance: `width(text(string, dy=height))+3`. Another text instance is then subtracted from this rectangle.

To create this parametric shape, it is required to pass the parameters to the `label(...)` call, as shown in symbol main. With this definition labels can then be conveniently created and in case the label structure should be changed later, it is possible to do so by only editing a few lines of the script.


## Defining symbol references

Symbols and symbol references are an important feature of the gdsII standard.  Symbols are created by placing symbol sections to the pls script. References are created using the `ref(...)` function:

```
SYMBOL sym1
  LAYER 1
    rect(10)

SYMBOL sym2
  LAYER 1
    text('foobar', dy=10)

SYMBOL main
  ref(sym1).array(2, 2, 5, 5)
  ref(sym2).translate(0,10).rotate(10)

  LAYER 2
    rect(5)
```

In this example, two symbols `sym1` and `sym2` are defined, each containing a simple geometric shape on layer 1. Then the symbol `main` is defined, which contains references to both shapes. Obviously, the referenced geometry cannot be altered except for translation, rotation or array formation. Adding, subtracting, growing or rounding corners are not available for references.

Because referenced symbols already contain layer definitions, it is not necessary to place the references in `LAYER` sections. Regular shapes can be added to the symbol in addition to references using `LAYER` sections.


## Defining and referencing parametric symbols

Using free parameters in the definition of symbols can be quite useful. In analogy to `SHAPE`s, this can be done by adding an argument list after the symbol name:

```
SYMBOL sym{}{:.0f}(a, b)
  LAYER 1
    rect(a).translate(-a-1, 0)
  LAYER 2
    rect(b).translate(a+1, 0)

SYMBOL main
  ref(sym, 10,  5)
  ref(sym,  5,  5)
  ref(sym,  5, 10)
```

Here, a parametric symbol with the name `sym{}{:.0f}` with two parameters `a` and `b` is defined (why there are curly braces in the name is explained below). The symbol contains translated rectangles with sizes specified by the two parameters on layer 1 and layer 2.

This parametric symbol is referenced with three different choices of `a` and `b` in the symbol `main`. The parameters are passed to the `ref()` function in addition to the symbol name.

Because the gdsII file format does not support parametric symbols, polyp will create as many gdsII symbols, as parameter choices exist in the layout script. To do so, polyp needs to be capable of creating a unique symbol name from a given parameter set. Therefore, the names of parametric symbols should contain as many `{}` placeholders as parameters exist. A placeholder is given by a pair of curly braces `{}`, optionally containing formatting options. In this example, the symbol name `sym{}{:.0f}` contains the placeholder `{}` for the parameters `a` and the placeholder `{:.0f}` for the parameter `b`. See the documentation of [python's format language](https://www.python.org/dev/peps/pep-3101/) for more details on placeholder structure.


## Imports

Any pls script can also serve as a library that can be references from other pls scripts: The `IMPORT` keyword followed by the path to another pls script allows to import shapes and symbols from the external file. Consider this example for a layout split across two different files lib.pls and main.pls:

lib.pls:
```
SHAPE externalShape(a, b)
  rect(a).rotate(b)
```

main.pls:
```
IMPORT lib.pls

SYMBOL main
  LAYER 0
    lib.externalShape(10, 60)
```

The `IMPORT` in main.pls loads all definitions from lib.pls which then can be referenced by `lub.name(...)`, where name is the name defined in lib.pls. To prevent naming collisions, the symbols from a library can also be made accessible under a custom name using the `AS` keyword:
```
IMPORT lib.pls AS sub
...
sub.externalShape(...)
```


## Named layers

The `LAYER` context also accepts names, not only numbers:

```
...
LAYER named_layer
  text('foobar', dy=10)
...
```

Because gdsII files do not support named layers, polyp will automatically assign a layer number and create a symbol called "legend", in which the layer name to layer number correspondence is written. To force a specific gdsII layer number and give the layer a name at the same time, the simply pass both number and name to the `LAYER` context:

```
...
LAYER 10 named_layer
  text('foobar', dy=10)
...
```

## Parameter sweeps

It is often desired to design a geometry with a free parameter and to place copies of this geometry with the free parameter being swept through a given range. Parametric geometry is possible with parametric `SHAPE`s or `SYMBOL`s, as shown before. To sweep paramters, the `.call(...)` method is used:

```
SHAPE shiftedCross(size, linewidth, xOffset, yOffset)
  (rect(size, linewidth)
  + rect(linewidth, size)).translate(xOffset, yOffset)

SYMBOL main
  LAYER param_sweeps
    shiftedCross.call(start=(5,.5,36,-10), step=(0,0,6,6), stop=(0,0,55,5))
```

This example defines a parametric shape `shiftedCross` with four free parameters. The line `shiftedCross.call(...)` then places instances of this shape with the four parameters varied as given by the `start`, `step` and `stop` arguments. The routine starts by choosing all parameters according to the `start`-list, namely `size=5`, `linewidth=.5`, `xOffset=36` and `yOffset=-10`. Each parameter is then incremented as specified by the respective number in the `step`-list until it reaches the value given in the `stop`-list. A `step` value of zero implies that the respective parameter is not swept at all. The parametric shape `shiftedCross` is created for all possible combinations of parameters.


## Globals

In larger layouts it is helpful to maintain a central list of global parameters, e.g. linewidths, minimum paddings or spacings etc. This is done using the `GLOBALS` context in polyp layout scripts:

```
GLOBALS
  linewidth = 15
  width = 100

SYMBOL main
  LAYER 0
    rect(linewidth, width)
```

The definitions from the `GLOBALS` section can be used anywhere in the layout script.


## Objects und unpacking

Objects can be created to group globally stored parameters:

```
GLOBALS
  optsA = {
    linewidth = 15
    width = 100
  }
  optsB = {
    linewidth = 15
    width = 100
  }

SHAPE wire(linewidth, width)
  rect(linewidth, width)


SYMBOL main
  LAYER 0
    wire(*optsA)
  LAYER 1
    wire(*optsB)
```

The unary `*` operator applied to objects unpacks the object into a parameter list. This way it is not necessary to write down all argument names anymore, which is helpful in layouts with many free parameters.

## QR codes

The `qrcode` native creates a qr code geometry from a given string. The optional named parameters `dx` and `dy` specify the size of the resulting code in x and y directions. With the `robust` parameter (1...4, higher=more robust, default 2) the redundancy in the generated code can be adjusted. The `res` parameter controls the number of "pixels" used in the qrcode. By default, the `res` is automatically chosen according to the input string.
