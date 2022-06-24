GLOBALS
  a = 5
  b = 13,
  c = 'kek'
  d = 10
  obj = {a = 5, b = 13,
         c = 'top',
         d = -20
  }

SHAPE s1()
  rect(a).rotate(b)
  - text(c, dy=a/3).rotate(d)

SHAPE s2(a, b, c, d)
  rect(a).rotate(b)
  - text(c, dy=a/3).rotate(d)

SYMBOL sym_{}_{}(a, b)
  LAYER 2
    rect(a, b)

SYMBOL sym2_{}(d)
  LAYER 3
    rect(d).rotate(b)

SYMBOL sym3_{}(t)
  LAYER 4
    text(t, dy=5)

SYMBOL _main_
  ref(sym, 1, 2)
  ref(sym2, d=20)
  ref(sym3, c)
  ref(sym3, 'rolf')

  LAYER hello
    s1()

  LAYER world
    s2(*obj, d=45)
    +s2(*obj, d=25)
