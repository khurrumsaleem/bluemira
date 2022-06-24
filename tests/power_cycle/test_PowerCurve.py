# Import
import sys

import matplotlib.pyplot as plt

from _TIAGO_FILES_.Tools import Tools as imported_tools
from bluemira.power_cycle.cycle import PowerCurve as imported_pc

# from scipy.interpolate import interp1d as imported_interp1d


# Print new run lines
imported_tools.print_header()

# Figure config
fig = plt.figure()
m_size = 100

# Test interp1d
eps = sys.float_info.epsilon
this_load = [6, 9, 7, 8]
this_time = [0, 4, 7, 8]
other_load = [2, 2, 2, 4, 4]
other_time = [2, 5, 7, 9, 10]

plt.grid()
plt.scatter(this_time, this_load, color="b", s=m_size)
plt.scatter(other_time, other_load, color="r", s=m_size)
plt.plot(this_time, this_load, color="b")
plt.plot(other_time, other_load, color="r")

# Test 'superimpose' method
this = imported_pc(this_load, this_time)
other = imported_pc(other_load, other_time)
another = this.superimpose(other)
print(another.load)
print(another.time)

plt.scatter(another.time, another.load, color="k", s=m_size / 2)
plt.plot(another.time, another.load, color="k")

# this_lookup = imported_interp1d(this_time, this_load)
# other_lookup = imported_interp1d(other_time, other_load)


# this_load = other_lookup(this_time)
# other_load = this_lookup(other_time)
# plt.scatter(this_time, this_load, color="r", s=m_size)
# plt.scatter(other_time, other_load, color="r", s=m_size)

plt.show()
