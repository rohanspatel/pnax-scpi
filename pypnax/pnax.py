
from typing import Callable
from skrf import Network
from pypnax.interface import _scpiInterface
from pypnax.ecal import ECal
from pypnax.utilities import _int, _averaging, _measurement_list
from pypnax.utilities import valid_measurement, snp_from_string, parse_frequency

class _Query:
    """ Sends a query each time the object is accessed and parses the response through the given
    function """

    def __init__(self, command: str | tuple[str, ...], parse: Callable[..., object]) -> None:

        self.commands = (command,) if isinstance(command, str) else command
        self.parse = parse

    def __set_name__(self, owner, name: str) -> None:

        self.name = name

    def __get__(self, config: "PNAXConfig", owner=None) -> object:

        if config is None:
            return self

        responses = [config.interface.query(c.format(ch=config.channel)) for c in self.commands]
        return self.parse(*responses)

    def __set__(self, config: "PNAXConfig", value) -> None:
        raise AttributeError(f"'{self.name}' is read from the instrument and cannot be set")


class PNAXConfig:
    """ Live view of a PNA-X channel's configuration; every access queries the instrument """

    identity = _Query("*IDN?", str)  # Manufacturer, Model, Serial, Firmware
    start_freq = _Query("SENS{ch}:FREQ:STAR?", float)  # Hz
    stop_freq = _Query("SENS{ch}:FREQ:STOP?", float)  # Hz
    num_points = _Query("SENS{ch}:SWE:POIN?", _int)  # Number of points in sweep
    power = _Query("SOUR{ch}:POW1?", float)  # dBm
    if_bandwidth = _Query("SENS{ch}:BWID?", float)  # Hz
    measurements = _Query("CALC{ch}:PAR:CAT:EXT?", _measurement_list)  # Currently defined traces
    save_format = _Query("MMEM:STOR:TRAC:FORM:SNP?", str)  # RI, MA, DB
    current_measurement = _Query("CALC{ch}:PAR:SEL?", str)  # Currently selected measurement name
    averaging = _Query(("SENS{ch}:AVER?", "SENS{ch}:AVER:COUN?"), _averaging)  # Average count, 0 if disabled

    def __init__(self, interface: _scpiInterface, channel: int = 1) -> None:

        self.interface = interface
        self.channel = channel

    @classmethod
    def fields(cls) -> list[str]:
        """ Names of all queryable configuration parameters """

        return [name for name, attr in vars(cls).items() if isinstance(attr, _Query)]

    def as_dict(self) -> dict[str, object]:
        """ Query every parameter once and return a snapshot, e.g. for logging with a measurement """

        return {"channel": self.channel} | {name: getattr(self, name) for name in self.fields()}

    def __repr__(self) -> str:
        return f"PNAXConfig({', '.join(f'{k}={v!r}' for k, v in self.as_dict().items())})"


class PNAX():

    def __init__(self, address: str, channel: int = 1, preset: bool = True) -> None:
        """ Opens a SCPI connection or retrives an existing one for the given IP """

        self.interface = _scpiInterface.get_shared(address)
        self.config = PNAXConfig(self.interface, channel)
        self.ecal = ECal(self)

        if preset:
            self.preset()

    def preset(self) -> None:
        """ Reset the instrument to its 'preset' state """

        self.interface.write("SYST:PRES")

    def set_frequency(
        self,
        start: str | float,
        stop: str | float, 
        step: str | float | None = None
    ) -> None:
        """ Set the frequency range (and step size) for the measurement """

        start = parse_frequency(str(start))
        stop = parse_frequency(str(stop))
        step = parse_frequency(str(step)) if step is not None else None

        self.interface.write(f"SENS{self.config.channel}:FREQ:STAR {start}")
        self.interface.write(f"SENS{self.config.channel}:FREQ:STOP {stop}")

        if step is not None:
            n_pts = int((float(stop) - float(start)) / float(step)) + 1
            self.set_sweep_points(n_pts)

    def set_sweep_points(self, points: int) -> None:
        """ Set the number of sweep points for the measurement """

        self.interface.write(f"SENS{self.config.channel}:SWE:POIN {points}")

    def set_if_bandwidth(self, bandwidth: str | float) -> None:
        """ Set the IF bandwidth for the measurement """
        
        bandwidth = parse_frequency(str(bandwidth))
        self.interface.write(f"SENS{self.config.channel}:BWID {bandwidth}")

    def set_averaging(self, count: int) -> None:
        """ Enable averaging if count > 1, otherwise disable averaging """

        if count < 1:
            self.interface.write(f"SENS{self.config.channel}:AVER OFF")
        else:
            self.interface.write(f"SENS{self.config.channel}:AVER ON")
            self.interface.write(f"SENS{self.config.channel}:AVER:COUN {count}")

    def _create_measurement(self, measurement: str, name: str) -> None:
        """ Create a new measurement with the given name """

        self.interface.write(f'CALC{self.config.channel}:PAR:DEF \"{name}\",{measurement}')

    def select_measurement(self, measurement: str) -> None:
        """ Select an existing measurement, or create a new one if it doesn't exist """

        measurement = measurement.strip().upper()
        if not valid_measurement(measurement):
            raise ValueError(f"Invalid measurement name: {measurement}")
        if not measurement.startswith("S"):
            measurement = f"S{measurement}"

        measurement_name_prefix = f"CH{self.config.channel}_{measurement}"

        measurement_name = None
        for existing_name in self.config.measurements:
            if existing_name.startswith(measurement_name_prefix):
                measurement_name = existing_name
                break
        else:
            measurement_name = f"{measurement_name_prefix}_{len(self.config.measurements) + 1}"
            self._create_measurement(measurement, measurement_name)

        self.interface.write(f"CALC{self.config.channel}:PAR:SEL \"{measurement_name}\"")

    def trigger(self) -> None:
        """ Triggers a single sweep, or multiple sweeps if averaging is enabled """

        ch = self.config.channel
        self.interface.write(f"SENS{ch}:AVER:CLE")  # Clear averaging for new measurement

        # Sweep enough times for a full averaging cycle
        if (avg := self.config.averaging) > 0:
            self.interface.write(f"SENS{ch}:SWE:GRO:COUN {avg}")
            self.interface.write(f"SENS{ch}:SWE:MODE GRO")

        # Just sweep once
        else:
            self.interface.write(f"SENS{ch}:SWE:MODE SING")

        self.interface.indefinite_wait()

    def measure(self, *ports: int) -> Network:
        """ Take a single sweep and return the S-parameters between the given ports

        eg. measure(1, 2) returns a 2-port Network containing S11, S21, S12 and S22
        """

        ports = sorted(set(ports))
        if not ports:
            raise ValueError("At least one port must be given")

        ch = self.config.channel

        # Define every S-parameter between the ports so the PNA sources from each of them
        for receiver in ports:
            for source in ports:
                self.select_measurement(f"S{receiver}{source}")

        self.trigger()

        port_list = ",".join(str(p) for p in ports)
        response = self.interface.query(f'CALC{ch}:DATA:SNP:PORT? "{port_list}"')

        return snp_from_string(response, len(ports), self.config.save_format)
