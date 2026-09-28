
from pypnax.interface import _scpiInterface

class PNAX():

    def __init__(self, address: str):
        """ Opens a SCPI connection or retrives an existing one for the given IP """

        self.interface = _scpiInterface.get_shared(address)

    def identify(self) -> str:
        """ Get the instrument identification string """

        return self.interface.query("*IDN?")
