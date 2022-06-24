GLOBALS
  a = 5
  b = 13,
  c = 'kek',
  d = 10
#  obj = {a: 5, "b": 13, c: "text"}

SHAPE s1()
  rect(a).rotate(b)
  - text(c, dy=a/3).rotate(d)

SHAPE s2(a, b, c, d)
  rect(a).rotate(b)
  - text(c, dy=a/3).rotate(d)

SYMBOL _main_
  LAYER 0
    s1()
#    s2(*obj, d=45)
