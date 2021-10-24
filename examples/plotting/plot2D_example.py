import bluemira
import bluemira.plotting._matplotlib as _matplotlib

plot2doptions = _matplotlib.MatplotlibOptions()
plotter2d = _matplotlib.PointsPlotter()
print(plotter2d.options.plane)

import bluemira.geometry as geo
points = [[0,0,0], [1,0,1], [0,0,1]]
wire = geo.tools.make_polygon(points, closed=True)
wpoints = wire.discretize(10).T
plotter2d(wpoints, show=True, block=True)

wplotter2d = _matplotlib.WirePlotter()
wplotter2d.plot(wire, show=True, block=True, ndiscr=10)

face = geo.face.BluemiraFace(wire)

fplotter2d = _matplotlib.FacePlotter()
fplotter2d.plot(face, show=True, block=True)