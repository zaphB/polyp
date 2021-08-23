IMPORT nestedlib.pls

SHAPE externalShape(x)
  rect(c=[-20,0], dx=2*x, dy=2*x)
  + nestedlib.nestedShape(x)

SYMBOL externalSymbol
LAYER named_layer
  text('external symbol', dy=5)
