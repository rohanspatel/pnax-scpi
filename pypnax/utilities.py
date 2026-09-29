
import skrf as rf
import numpy as np

def complex_s(a: np.ndarray, b: np.ndarray, fmt: str = "RI") -> np.ndarray:
    """ Calculate complex S-parameters from two arrays of real numbers in the given format """

    fmt = fmt.upper()

    if fmt == "RI":
        return a + 1j * b
    elif fmt == "MA":
        return a * np.exp(1j * np.radians(b))
    elif fmt == "DB":
        return 10 ** (a / 20) * np.exp(1j * np.radians(b))
    else:
        raise ValueError(f"Invalid format: {fmt}")

def snp_from_string(string: str, n_ports: int, fmt: str = "RI") -> rf.Network:
    """ Convert a string of comma separated floats into a scikit-rf Network object """

    n_columns = n_ports * n_ports * 2 + 1

    data = np.array(string.split(","), dtype=float)
    data = data.reshape((n_columns, -1)).T

    freqs = rf.Frequency.from_f(data[:, 0], unit="Hz")
    s_params = complex_s(data[:, 1::2], data[:, 2::2], fmt=fmt)
    s_params = s_params.reshape((-1, n_ports, n_ports))

    return rf.Network(frequency=freqs, s=s_params)

def _int(value: str) -> int:
    """ Cast a string to an integer """
    return int(float(value))

def _csv_strings(value: str) -> list[str]:
    """ Split a string of comma separated values into a list of strings """
    return value.split(",")
