# Import
from _TIAGO_FILES_.Tools import Tools as imported_tools
from bluemira.power_cycle.base import PowerData as imported_class

# Print new run lines
imported_tools.print_header()

# Data
test_time = [0, 4, 7, 8]
test_data = [6, 9, 7, 8]

# Create instance of PowerData
test_instance = imported_class(test_time, test_data)

# Print instance attributes
print(test_instance.plot_defaults)
print(test_instance.time)
print(test_instance.data)

# Test validation method
check_if_of_class = imported_class._validate_PowerData(test_instance)
print(check_if_of_class)

# Test visualization method
test_instance.plot()
