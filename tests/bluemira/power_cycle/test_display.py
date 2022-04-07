# Import packages
import json
import os

# Start script
print("\n")

# Path of current script
this_path = os.path.abspath(__file__)
print(this_path)
print("\n")

# Path of current directory
dir_path = os.path.dirname(this_path)
print(dir_path)
print("\n")

# Path of `display_units.json` file in current directory
json_path = os.path.join(dir_path, "display_units.json")
print(json_path)
print("\n")

# Read `display_units.json` file
with open(json_path) as json_file:
    display_units = json.load(json_file)
    print(display_units)
print("\n")

# Display JSON data
print(json.dumps(display_units, indent=4))
print("\n")

# Read data as dictionary
print(display_units["Application"])
print("\n")

print(display_units["Display Units"])
print("\n")

print(display_units["Display Units"]["Tables"])
print("\n")

print(display_units["Display Units"]["Tables"]["mass-flow"])
print("\n")
