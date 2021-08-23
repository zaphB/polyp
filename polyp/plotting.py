import gdspy as _gdspy

import matplotlib.pyplot as _plt
import matplotlib.patches as _patches


def plot(gds, symName=None, layers=range(0,2**8), hatches=[]):
    if type(gds) is str:
      gds = _gdspy.GdsLibrary().read_gds(gds).cells
    if type(layers) is dict:
      colors = layers
      layers = list(layers.keys())
    else:
      colors = {}

    if type(hatches) is list:
      hatches = {i: h for i, h in enumerate(hatches)}

    allColors = list(_plt.rcParams['axes.prop_cycle'].by_key()['color'])
    #allHatches = ['-', '+', 'x', '\\', '*', 'o', 'O', '.']
    allHatches = ['\\', '/', '-', '|']

    def getColor(layer):
      if layer not in colors.keys():
        colors[layer] = allColors.pop(0)
        allColors.append(colors[layer])
      return colors[layer]

    def getHatch(layer):
      if layer not in hatches.keys():
        hatches[layer] = allHatches.pop(0)
        allHatches.append(hatches[layer])
      return hatches[layer]

    if symName is None:
      symName = list(gds.keys())[0]

    minX, maxX = _plt.gca().get_xlim()
    minY, maxY = _plt.gca().get_ylim()

    labels = []
    for layer, polys in sorted([(layer, polys) for ((layer, datatype), polys)
                                  in gds[symName].get_polygons(by_spec=True).items()],
                               key=lambda e: e[0]):
      if layer not in layers:
        continue
      for path in polys:

        p = _patches.Polygon(path,
                             color=getColor(layer),
                             #hatch=getHatch(layer),
                             zorder=layer+2,
                             label="Layer {}".format(layer),
                             lw=0, fill=True, alpha=0.4)
        if p.get_label() in labels:
          p.set_label(None)
        else:
          labels.append(p.get_label())

        maxX = max(maxX, *[x for x,y in p.xy])
        maxY = max(maxY, *[y for x,y in p.xy])
        minX = min(minX, *[x for x,y in p.xy])
        minY = min(minY, *[y for x,y in p.xy])
        _plt.gca().add_patch(p)

    xCen = .5*(maxX + minX)
    yCen = .5*(maxY + minY)
    ran = max(maxX - minX, maxY - minY)
    _plt.xlim(xCen - .51*ran, xCen + .51*ran)
    _plt.ylim(yCen - .51*ran, yCen + .51*ran)
    _plt.gca().set_aspect('equal')
