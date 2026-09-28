
from pypnax.interface import _scpiInterface

class ECal():

    def __init__(self, address: str):
        """ Opens a SCPI connection or retrives an existing one for the given IP """

        self.interface = _scpiInterface.get_shared(address)

        # Input validation
        self._ecal_ports = ["A", "B", "C", "D"]
        self._ecal_port_pairs = ["AB", "AC", "AD", "BC", "BD", "CD"]
        self._ecal_reflect_states = {
            "open": 1,
            "short": 2,
            "impedance1": 3,
            "impedance2": 4,
        }
        self._ecal_transmit_states = {
            "through": 1,
            "confidence": 2,
        }

    def switch_state(
        self,
        port: str,
        state: str | int
    ) -> None:

        port = format_ports(port)

        if len(port) == 1:
            if port not in self._ecal_ports:
                raise ValueError(f"Invalid port: {port}")
            self._set_reflect_state(port, state)
        elif len(port) == 2:
            if port not in self._ecal_port_pairs:
                raise ValueError(f"Invalid port pair: {port}")
            self._set_transmit_state(port, state)
        else:
            raise ValueError(f"Invalid port: {port}")

    def _set_reflect_state(
        self,
        port: str,
        state: str | int
    ) -> None:

        if isinstance(state, str):
            state = state.lower()
            if state not in self._ecal_reflect_states:
                raise ValueError(f"Invalid reflect state: {state}")
            state = self._ecal_reflect_states[state]
        elif isinstance(state, int):
            if state not in self._ecal_reflect_states.values():
                raise ValueError(f"Invalid reflect state: {state}")
        else:
            raise ValueError(f"Invalid reflect state: {state}")

        self.interface.write(f"CONT:ECAL:MOD:PATH:STAT {port},{state}")

    def _set_transmit_state(
        self,
        port: str,
        state: str | int
    ) -> None:

        if isinstance(state, str):
            state = state.lower()
            if state not in self._ecal_transmit_states:
                raise ValueError(f"Invalid transmit state: {state}")
            state = self._ecal_transmit_states[state]
        elif isinstance(state, int):
            if state not in self._ecal_transmit_states.values():
                raise ValueError(f"Invalid transmit state: {state}")
        else:
            raise ValueError(f"Invalid transmit state: {state}")

        self.interface.write(f"CONT:ECAL:MOD:PATH:STAT {port},{state}")

def format_ports(port: str) -> str:
    """ Format the port string to be uppercase and without whitespace """

    p = list(port.strip().upper())
    p.sort()

    return "".join(p)