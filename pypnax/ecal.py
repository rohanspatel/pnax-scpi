
from skrf import Network
from pypnax.utilities import snp_from_string

class ECal():

    def __init__(self, pnax) -> None:
        """ Class for specifically controlling the ECal module connected to a PNA-X via USB """

        self._pnax = pnax
        self.interface = pnax.interface

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
        """ Switch the state of the ECal module
        
        Ports
        -----
        Reflection States: A, B, C, D
        Transmission States: AB, AC, AD, BC, BD, CD

        States
        ------
        Reflection States: open, short, impedance1, impedance2
        Transmission States: through, confidence
        """
        
        port, code = self._resolve(port, state)
        self.interface.write(f"CONT:ECAL:MOD:PATH:STAT {port},{code}")

    def get_state_data(
        self,
        port: str,
        state: str | int
    ) -> Network:
        """ Gets S-parameters from the ECal's internal memory for the given port and state

        Ports
        -----
        Reflection States: A, B, C, D
        Transmission States: AB, AC, AD, BC, BD, CD

        States
        ------
        Reflection States: open, short, impedance1, impedance2
        Transmission States: through, confidence
        """

        format = self._pnax.config.save_format

        port, code = self._resolve(port, state)
        data_string = self.interface.query(f"SENS:CORR:CKIT:ECAL:PATH:DATA? {port},{code}")

        return snp_from_string(data_string, len(port), fmt=format)

    def _resolve(
        self,
        port: str,
        state: str | int
    ) -> tuple[str, int]:
        """ Validates the port and state inputs and returns the SCPI-readable codes """

        port = format_ports(port)

        if len(port) == 1:
            if port not in self._ecal_ports:
                raise ValueError(f"Invalid port: {port}")
            states = self._ecal_reflect_states
        elif len(port) == 2:
            if port not in self._ecal_port_pairs:
                raise ValueError(f"Invalid port pair: {port}")
            states = self._ecal_transmit_states
        else:
            raise ValueError(f"Invalid port: {port}")

        return port, self._resolve_state(state, states)

    @staticmethod
    def _resolve_state(
        state: str | int,
        states: dict[str, int]
    ) -> int:
        """ Validates a human-readable state using a dictionary of valid state/SCPI-code pairs """

        if isinstance(state, str):
            state = state.lower()
            if state not in states:
                raise ValueError(f"Invalid state: {state}")
            return states[state]
        elif isinstance(state, int):
            if state not in states.values():
                raise ValueError(f"Invalid state: {state}")
            return state
        else:
            raise ValueError(f"Invalid state: {state}")

def format_ports(port: str) -> str:
    """ Format the port string to be uppercase, without whitespace, and in alphabetical order """
    p = list(port.strip().upper())
    p.sort()

    return "".join(p)