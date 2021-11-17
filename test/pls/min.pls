SYMBOL sym{}{:.0f}(a, b)
  LAYER 1
    rect(a).translate(-a-1, 0)
  LAYER 2
    rect(b).translate(a+1, 0)

SYMBOL main
  ref(sym, 10,  5)
  ref(sym,  5,  5)
  ref(sym,  5, 10)
