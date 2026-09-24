#!/usr/bin/env python

import sys
import time
import pyvisa

TIMEOUT_MS = 10000
TERMINATION_CHAR = "\n"

class scpiInterface:

    def __init__(
        self,
        ip_address: str = "192.168.1.1",
    ) -> None:
        """ Set default values and other class variables """

        self.ip_address = ip_address
        self.timeout_ms = TIMEOUT_MS
        self.term_char = TERMINATION_CHAR

        self.resource_string = f"TCPIP0::{ip_address}::inst0::INSTR"
        self.rm = pyvisa.ResourceManager()
        self.inst = None

        self.connect()

    def connect(self) -> None:
        """ Open the VISA session to the instrument """

        try:
            self.inst = self.rm.open_resource(self.resource_string)
            self.inst.timeout = self.timeout_ms
            self.inst.read_termination = self.term_char
            self.inst.write_termination = self.term_char
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


if __name__ == "__main__":

    interface = _scpiInterface()
    idn = interface.query("*IDN?")
    print(f"Instrument ID: {idn}")
