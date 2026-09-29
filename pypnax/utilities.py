
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

    # 2-port data ordered column-wise (S11, S21, S12, S22); N-port data row-wise
    if n_ports == 2:
        s_params = s_params.transpose(0, 2, 1)

    return rf.Network(frequency=freqs, s=s_params)

def valid_measurement(measurement: str, n_ports: int = 2) -> bool:
    """ Check if a measurement name is valid for the given number of ports (eg. S11, S21, etc.) """

    if len(measurement) == 3 and measurement.startswith("S"):
        measurement = measurement[1:]
    elif len(measurement) == 2:
        pass
    else:
        return False

    for char in measurement:
        try:
            port = int(char)
        except ValueError:
            return False

        if port < 1 or port > n_ports:
            return False

    return True

def _int(value: str) -> int:
    """ Cast a string to an integer """
    return int(float(value))

def _measurement_list(value: str) -> list[str]:
    """ Returns a list of measurement names from the SCPI response string """

    response_list = value.strip('"').split(",")     # Contains names and measurement types
    return [r for r in response_list if not valid_measurement(r)]   # Removes measurement types
