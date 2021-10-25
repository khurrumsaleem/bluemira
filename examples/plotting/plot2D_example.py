import bluemira
import bluemira.plotting._matplotlib as _matplotlib

plot2doptions = _matplotlib.MatplotlibOptions()
plotter2d = _matplotlib.PointsPlotter()
print(plotter2d.options.plane)

import bluemira.geometry as geo
points = [[0,0,0], [1,0,1], [0,0,1]]
wire = geo.tools.make_polygon(points, closed=True)
wpoints = wire.discretize(10).T
#plotter2d(wpoints, show=True, block=True)

wplotter2d = _matplotlib.WirePlotter()
#wplotter2d.plot(wire, show=True, block=True, ndiscr=10)

face = geo.face.BluemiraFace(wire)

fplotter2d = _matplotlib.FacePlotter()
#fplotter2d.plot(face, show=True, block=True)

import copy
wire1 = copy.deepcopy(wire)
wire1.translate((0,0,1))

import bluemira.plotting._matplotlib as _mpl
#_mpl.plot([wire1, wire], plot2doptions, show=True, block=True)

ax = wplotter2d.plot(wire, show=False, block=True, ndiscr=3, byedges=True)
wplotter2d.plot(wire1, ax=ax, show=True, block=True, ndiscr=3, byedges=True)

