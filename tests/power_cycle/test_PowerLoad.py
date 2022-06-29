# Import
import matplotlib.pyplot as plt

# from scipy.interpolate import interp1d as imported_interp1d
from _TIAGO_FILES_.Tools import Tools as imported_tools
from bluemira.power_cycle.base import PowerData as imported_class_1
from bluemira.power_cycle.base import PowerLoad as imported_class_2

# import numpy as np


# Header
imported_tools.print_header("Test PowerLoad")

# Test data
name_1 = "test_1"
time_1 = [0, 4, 7, 8]
data_1 = [6, 9, 7, 8]
load_1 = imported_class_1(name_1, time_1, data_1)
model_1 = "ramp"
name_2 = "test_2"
time_2 = [2, 5, 7, 9, 10]
data_2 = [2, 2, 2, 4, 4]
load_2 = imported_class_1(name_2, time_2, data_2)
model_2 = "step"

# Create instances of PowerLoad
instance_1 = imported_class_2(load_1, model_1, name="Test 1")
instance_2 = imported_class_2(load_2, model_2, name="Test 2")

# Test `_refine_vector` method
refined_time_1 = imported_class_2._refine_vector(time_1, 3)
print(refined_time_1)
refined_time_2 = imported_class_2._refine_vector(time_2, 0)
print(refined_time_2)

# Test visualization method
plt.figure()
plt.grid()
instance_1.plot(c="r")
instance_2.plot(c="b")

# Test addition method
plt.figure()
plt.grid()
instance_3 = instance_1 + instance_2
instance_3.plot(detailed=True)

# Show plots
plt.show()

"""
# Plot data
plt.scatter(time_1, data_1, c='b', s=100)
plt.scatter(time_2, data_2, c='r', s=100)



# Interpolation test times
test_time = np.arange(-1, 11 + 1, 0.5).tolist()
print(test_time)

# Interpolation test
curve_1 = instance_1.curve(test_time)
curve_2 = instance_2.curve(test_time)
print(curve_1)
print(curve_2)

# Plot tests
plt.scatter(test_time, curve_1, c='b')
plt.scatter(test_time, curve_2, c='r')
plt.show()
"""

"""
# Data
test_time = [0, 4, 7, 8]
test_data = [6, 9, 7, 8]

# Create instance of GenericPowerLoad
test_instance = imported_class(test_time, test_data)

# Create GenericPowerLoad instance
test_model = "ramp"
test_vector1 = "[0, 5, 3, 15, 2]"
test_vector2 = "[10, 12, 14, 16, 18]"
test_GPL = GPL(test_model, test_vector1, test_vector2)
curve = test_GPL.generate_curve()

print('\n')
print(test_GPL.__class__.__name__)
print(type(test_GPL))
print(test_model)
print(test_vector1)
print(test_vector2)

print('\n')
print(curve["power"])
print(curve["times"])

# Plot curve
times = curve["times"]
power = curve["power"]

# Manipulate curve
power = np.divide(power, 2)

plt.scatter(times, power)
plt.plot(times, power)
plt.title('Example GenericPowerLoad Curve')
plt.xlabel('time (s)')
plt.ylabel('power (W)')
plt.grid()
plt.show()

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

# Display plot
plt.show()
"""
