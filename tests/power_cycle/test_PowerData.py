# Import
import matplotlib.pyplot as plt

from _TIAGO_FILES_.Tools import Tools as imported_tools
from bluemira.power_cycle.base import PowerData as imported_class

# Header
imported_tools.print_header("Test PowerData")

# Test data
test_time = [0, 4, 7, 8]
test_data = [6, 9, 7, 8]

# Create instance of PowerData
test_instance = imported_class(test_time, test_data)

# Print instance attributes
print(test_instance.plot_defaults)
print(test_instance.time)
print(test_instance.data)

# Test validation method
test_instance = imported_class._validate_PowerData(test_instance)
print("No errors raised on validation!")

# Test visualization method
test_instance.plot()

# Show plots
plt.show()
