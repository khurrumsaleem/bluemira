"""
Programming tools to make my life easier
"""

# Import necessary packages
# import os
# import sys
# import json
# import numpy as np


class Tools:

    #
    @staticmethod
    def print_header():
        """
        Print a set of header lines to separate different script runs
        in the terminal.
        """
        # Header
        header = " NEW RUN "
        header = header.center(72, "=")

        # Print Header
        print("\n\n")
        print(header)
        print("\n")
