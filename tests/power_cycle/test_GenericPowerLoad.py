# Import
import matplotlib.pyplot as plt
import numpy as np

from _TIAGO_FILES_.Tools import Tools as TFT
from bluemira.power_cycle.cycle import GenericPowerLoad as GPL

# Print new run lines (test GenericPowerLoad class)
TFT.print_header()

# Create GenericPowerLoad instance
test_model = "ramp"
test_vector1 = "[0, 5, 3, 15, 2]"
test_vector2 = "[10, 12, 14, 16, 18]"
test_GPL = GPL(test_model, test_vector1, test_vector2)
curve = test_GPL.generate_curve()

print("\n")
print(test_GPL.__class__.__name__)
print(type(test_GPL))
print(test_model)
print(test_vector1)
print(test_vector2)

print("\n")
print(curve["power"])
print(curve["times"])

# Plot curve
times = curve["times"]
power = curve["power"]

# Manipulate curve
power = np.divide(power, 2)

plt.scatter(times, power)
plt.plot(times, power)
plt.title("Example GenericPowerLoad Curve")
plt.xlabel("time (s)")
plt.ylabel("power (W)")
plt.grid()
plt.show()
