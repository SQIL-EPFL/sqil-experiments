"""
Two-qubit setup for multiplexed readout with the SG2 reset 

Copy of setup_reset.py (same instrument, same storage) with a second qubit:
- readout of q0 and q1 on the QA channel (frequency multiplexed)
- drive of q0 and q1 on SG channel 1, LF mode (common drive line, ~100 MHz)
- reset tones of q0 and q1 on SG channel 2, RF mode (~7 GHz), one aux line
  per qubit ("q0/aux", "q1/aux"), played by ResetOperations.passive_reset
- its own QPU file (qpu_mux_reset_ar.json)
"""

import os

from laboneq.contrib.example_helpers.generate_device_setup import (
    create_connection,
    generate_device_setup,
)
from laboneq.dsl.quantum import QPU
from laboneq.simple import Calibration, PortMode, SignalCalibration
from sqil_core.experiment import bind_instrument_qubit

from sqil_experiments.qpu.sqil_transmon.operations_multiplexed import ResetOperations
from sqil_experiments.qpu.sqil_transmon.qubit import SqilTransmon

n_qubits = 2

data_folder_name = "20261210_20251110_Fluxonoim_AQUA"

# Data storage
db_root = r"Z:\Projects\Transmon\multiplexed"
db_root_local = r"C:\Users\sqil\Desktop\data_local"
storage = {
    "db_type": "plottr",
    "db_path": os.path.join(db_root, data_folder_name),
    "db_path_local": os.path.join(db_root_local, data_folder_name),
    "qpu_filename": "qpu_mux_reset_ar.json",
}


# Zurich Instruments setup
def generate_zi_setup():
    # q0: readout on the QA channel, drive (+ drive_ef) on SG channel 1
    setup = generate_device_setup(
        number_qubits=1,
        shfqc=[
            {
                "serial": "dev12537",
                "number_of_channels": 2,
                "options": "SHFQC/LRT/PLUS/QC2CH",
            }
        ],
        include_flux_lines=False,
        multiplex_drive_lines=True,
        query_options=False,
    )

    # q1: same readout channel and same drive channel as q0
    # reset tones of both qubits: aux lines on SG channel 2 (index 1)
    setup.add_connections(
        "shfqc_0",
        create_connection(to_signal="q1/measure", ports="QACHANNELS/0/OUTPUT"),
        create_connection(to_signal="q1/acquire", ports="QACHANNELS/0/INPUT"),
        create_connection(to_signal="q1/drive", ports="SGCHANNELS/0/OUTPUT"),
        create_connection(to_signal="q0/aux", ports="SGCHANNELS/1/OUTPUT"),
        create_connection(to_signal="q1/aux", ports="SGCHANNELS/1/OUTPUT"),
    )

    # Drives (SG channel 1) through the LF path, as in setup_reset.py
    setup.set_calibration(
        Calibration(
            {
                setup.logical_signal_by_uid(uid): SignalCalibration(
                    port_mode=PortMode.LF
                )
                for uid in ["q0/drive", "q0/drive_ef", "q1/drive"]
            }
        )
    )
    return setup


def generate_qpu(zi_setup):
    qubits = SqilTransmon.from_device_setup(zi_setup)
    quantum_operations = ResetOperations()
    qpu = QPU(qubits, quantum_operations)

    # Settings shared by both qubits: they use the same ports, so the
    # center frequencies and ranges must be the same
    for qubit in qpu.quantum_elements:
        qubit.update(
            **{
                "readout_lo_frequency": 7e9,
                "readout_range_out": 10,
                "readout_range_in": -5,
                "drive_lo_frequency": 100e6,  # LF path: multiples of 100 MHz
                "drive_range": 5,  # LF path: max +5 dBm
                "aux_lo_frequency": 7e9,  # RF path: multiples of 200 MHz
                "aux_range": 10,
            }
        )
    return qpu


instruments = {
    "yoko0": {
        "type": "CS",
        "model": "Yokogawa_GS200",
        "address": "TCPIP0::192.168.1.51::inst0::INSTR",
        "name": "yoko0",
        "ramp_step": 1e-6,
        "ramp_step_delay": 0.008,
        "current_range": 1e-3,  # Change when at 0 flux
        "variables": {"current": bind_instrument_qubit("current", "q0")},
    },
    "zi": {
        "type": "ZI",
        "address": "localhost",
        "generate_setup": generate_zi_setup,
        "generate_qpu": generate_qpu,
    },
}
