#!/usr/bin/env python

import sys
import pyvisa

class _scpiInterface:

    _TIMEOUT_MS = 10000
    _TERMINATION_CHAR = "\n"

    _INSTANCES: dict[str, "_scpiInterface"] = {}

    def __init__(
        self,
        ip_address: str = "192.168.1.1",
    ) -> None:
        """ Set default values and other class variables """

        self.ip_address = ip_address

        self.resource_string = f"TCPIP0::{ip_address}::inst0::INSTR"
        self.rm = pyvisa.ResourceManager()
        self.inst = None

        self.connect()

    @classmethod
    def get_shared(cls, ip_address: str) -> "_scpiInterface":
        """ Get a shared instance of the _scpiInterface class """

        ip_address = strip_ip(ip_address)

        if ip_address not in cls._INSTANCES:
            cls._INSTANCES[ip_address] = cls(ip_address)

        return cls._INSTANCES[ip_address]

    def connect(self) -> None:
        """ Open the VISA session to the instrument """

        try:
            self.inst = self.rm.open_resource(self.resource_string)
            self.inst.timeout = self._TIMEOUT_MS
            self.inst.read_termination = self._TERMINATION_CHAR
            self.inst.write_termination = self._TERMINATION_CHAR
            print(f"Connected to: {self.resource_string}")

        except pyvisa.errors.VisaIOError as e:
            print(f"ERROR: Could not connect to {self.resource_string}\n{e}")
            sys.exit(1)

    def close(self) -> None:
        """ Close the VISA session """

        if self.inst is not None:
            self.inst.close()
            print("Connection closed.")

    def write(self, command: str) -> None:
        """ Send a SCPI command with no expected response """

        self.inst.write(command)

    def query(self, command: str) -> str:
        """ Send a SCPI query and return the response """

        response = self.inst.query(command)
        return response.strip()

    def wait(self) -> None:
        """ Wait for the instrument to complete its current operation """

        self.query("*OPC?")


def strip_ip(ip_address: str) -> str:
    """ Remove any whitespace and leading zeros from the IP address """

    octets = ip_address.strip().split(".")
    octets = [str(int(octet)) for octet in octets]
    return ".".join(octets)


if __name__ == "__main__":

    interface = _scpiInterface()
    idn = interface.query("*IDN?")
    print(f"Instrument ID: {idn}")
