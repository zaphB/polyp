# circle with radius r
SHAPE circle(r)
  rect(r).round(r)

# ellipse with horizontal radius r1 and
# vertical radius r2
SHAPE ellipse(r1, r2)
  circle(2).scale(r1, r2)

# ellipse that is x-shifted and changes height
# as a function of k (used for parameter sweep)
SHAPE shiftedEllipse(r1, r2, k)
  ellipse(r1/(1+abs(k)), r2*(1+abs(k)))
      .translate(k*50,0)


SYMBOL main
  # simple example with just circles
  LAYER 0
    circle(1).array(20,2,1,1)
    +circle(sqrt(2)).array(21,3,.49,.5)

  # subtract array of identical ellipses from a rectangle
  LAYER 1
    (rect(100,3) - ellipse(2,1).array(35,1,1,1)
      ).translate(0,-5)

  # subtract array of ellipses with swept parameters
  LAYER 2
    (rect(120,5)
      - shiftedEllipse.call(
          start=(  2,  1,  -1),
          step=(   0,  0,  .1),
          stop=(   0,  0,   1))
    ).translate(0,-13)

