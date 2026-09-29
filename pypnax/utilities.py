
def _int(value: str) -> int:
    """ Cast a string to an integer """
    return int(float(value))

def _csv_strings(value: str) -> list[str]:
    """ Split a string of comma separated values into a list of strings """
    return value.split(",")
