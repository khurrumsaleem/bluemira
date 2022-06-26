"""
Useful methods for multiple Power Cycle classes
"""


class PowerCycleUtilities:
    @staticmethod
    def add_dict_entries(dictionary, new_entries):
        """
        Add (key,value) pairs to a dictionary, only if they are not
        already specified (i.e. no substitutions). If dictionary is
        empty, returns only `new_entries`.
        """

        # Validate whether `dictionary` exists (i.e. not empty)
        if dictionary:

            # Keys of new entries
            new_entries_keys = new_entries.keys()

            # For each key
            for key in new_entries_keys:

                # Current entry value
                value = new_entries[key]

                # Add entry to dictionary, if not yet there
                dictionary.setdefault(key, value)
        else:

            # For empty `dictionary`, output only `new_entries`
            dictionary = new_entries

        # Output extended dictionary
        return dictionary
