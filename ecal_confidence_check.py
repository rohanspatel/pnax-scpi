
""" ECal Confidence Check Script

This script is an extension to the built-in ECal confidence check on the connected ECal module.  It
all the internal terminations of the ECal using the currently applied calibration, and compares to
the S-parameters stored in the ECal's internal memory.
"""

import time
import pathlib
import matplotlib.pyplot as plt
import skrf as rf
from pypnax.pnax import PNAX

START_FREQUENCY = "10MHz"
STOP_FREQUENCY = "1GHz"
FREQUENCY_STEP = "100kHz"
IF_BANDWIDTH = "10kHz"
AVERAGING = 3

PNAX_ECAL_MAPPING = {
    3: "D",
    4: "C",
}

WORKING_DIRECTORY = pathlib.Path(__file__).parent.resolve()
(OUTPUT_DIRECTORY := WORKING_DIRECTORY / "confidence_check").mkdir(exist_ok=True)


def to_pnax_port_order(calibration: rf.Network, pnax_ports: list[int]) -> rf.Network:
    """ Reorder ECal data (stored in alphabetical ECal port order) to match the sorted PNA ports """

    ecal_ports = [PNAX_ECAL_MAPPING[p] for p in sorted(pnax_ports)]
    order = [sorted(ecal_ports).index(e) for e in ecal_ports]
    s = calibration.s[:, order][:, :, order]

    return rf.Network(frequency=calibration.frequency, s=s, name=calibration.name)


def plot_two_port(measured: rf.Network, calibration: rf.Network, title: str) -> plt.Figure:
    """ Plot magnitude and phase of each S-parameter, with subfigures laid out like the S-matrix """

    fig = plt.figure(figsize=(20, 10), layout="constrained")
    subfigs = fig.subfigures(2, 2)

    for m in range(2):
        for n in range(2):
            ax_db, ax_deg = subfigs[m, n].subplots(1, 2)

            measured.plot_s_db(m=m, n=n, ax=ax_db, label="Measured Data")
            calibration.plot_s_db(m=m, n=n, ax=ax_db, label="Calibration Data")

            measured.plot_s_deg(m=m, n=n, ax=ax_deg, label="Measured Data")
            calibration.plot_s_deg(m=m, n=n, ax=ax_deg, label="Calibration Data")

            subfigs[m, n].suptitle(f"S{m + 1}{n + 1}")

    fig.suptitle(title)
    return fig

if __name__ == "__main__":

    pnax = PNAX("192.168.1.1")
    pnax.set_frequency(START_FREQUENCY, STOP_FREQUENCY, FREQUENCY_STEP)
    pnax.set_averaging(AVERAGING)
    pnax.set_if_bandwidth(IF_BANDWIDTH)

    print("Calibrate the PNA using any calibration method")
    print("Enter the name of the calibration to store outputs separately")
    calibration_name = input(">>> ")

    if calibration_name:
        (output_dir := OUTPUT_DIRECTORY / calibration_name).mkdir(exist_ok=True)
    else:
        output_dir = OUTPUT_DIRECTORY

    # Reflection Measurements
    for termination in ["open", "short", "impedance1", "impedance2"]:
        for pnax_port in PNAX_ECAL_MAPPING.keys():

            ecal_port = PNAX_ECAL_MAPPING[pnax_port]

            print(f"Measuring {termination} on Port {pnax_port}{ecal_port}...")
            filename = f"{termination}_Port-{pnax_port}{ecal_port}"

            fig, axes = plt.subplots(1, 2, figsize=(12, 5))

            pnax.ecal.switch_state(ecal_port, termination)
            time.sleep(2)

            calibration_data = pnax.ecal.get_state_data(ecal_port, termination)
            measured_data = pnax.measure(pnax_port)
            calibration_data.write_touchstone(output_dir / f"calibration_{filename}.s1p")
            measured_data.write_touchstone(output_dir / f"measured_{filename}.s1p")

            measured_data.plot_s_db(ax=axes[0], label="Measured Data")
            calibration_data.plot_s_db(ax=axes[0], label="Calibration Data")

            measured_data.plot_s_deg(ax=axes[1], label="Measured Data")
            calibration_data.plot_s_deg(ax=axes[1], label="Calibration Data")

            fig.suptitle(f"{termination.upper()} on Port {pnax_port}{ecal_port}")

            plt.savefig(output_dir / f"{filename}.png")
            plt.close(fig)

    # Transmission Measurements
    for termination in ["through", "confidence"]:

        available_ports = list(PNAX_ECAL_MAPPING.keys())

        pnax_port_pairs = []
        ecal_port_pairs = []
        for port in available_ports:
            for other_port in available_ports:
                if port != other_port:
                    pnax_port_pairs.append(f"{port}{other_port}")
                    ecal_port_pairs.append(f"{PNAX_ECAL_MAPPING[port]}{PNAX_ECAL_MAPPING[other_port]}")

        for pnax_port_pair, ecal_port_pair in zip(pnax_port_pairs, ecal_port_pairs):

            print(f"Measuring {termination} on Port {pnax_port_pair}{ecal_port_pair}...")
            filename = f"{termination}_Port-{pnax_port_pair}{ecal_port_pair}"

            pnax.ecal.switch_state(ecal_port_pair, termination)
            time.sleep(2)

            pnax_ports = [int(p) for p in pnax_port_pair]
            calibration_data = pnax.ecal.get_state_data(ecal_port_pair, termination)
            calibration_data = to_pnax_port_order(calibration_data, pnax_ports)
            measured_data = pnax.measure(*pnax_ports)
            calibration_data.write_touchstone(output_dir / f"calibration_{filename}.s2p")
            measured_data.write_touchstone(output_dir / f"measured_{filename}.s2p")

            title = f"{termination.upper()} on Port {pnax_port_pair}{ecal_port_pair}"
            fig = plot_two_port(measured_data, calibration_data, title)

            fig.savefig(output_dir / f"{filename}.png")
            plt.close(fig)
