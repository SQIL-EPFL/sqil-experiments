"""
Setup example for continuous wave measurements.
See how to connect to different types of instruments and how to
bind the instruments to QPU parameters.
"""

import os

from laboneq.dsl.quantum import QPU
from sqil_core.experiment import bind_instrument_qubit

from sqil_experiments.qpu.cw.operations import CwQubitOperations
from sqil_experiments.qpu.cw.qubit import CwQubit

# TODO: update cooldown name
data_folder_name = "my_cooldown"
n_qubits = 1

# Data storage
db_root = r""  # TODO: update database folder, e.g. Z:\Projects\...
db_root_local = r"C:\Users\sqil\Desktop\data_local"
storage = {
    "db_type": "plottr",
    "db_path": os.path.join(db_root, data_folder_name),
    "db_path_local": os.path.join(db_root_local, data_folder_name),
    "qpu_filename": "qpu.json",
}


def generate_qpu(*args):
    qubits = [CwQubit(f"q{i}") for i in range(n_qubits)]
    quantum_operations = CwQubitOperations()
    qpu = QPU(qubits, quantum_operations)
    return qpu


# Instruments
instruments = {
    "q0_drive": {
        "type": "RF",
        "model": "RohdeSchwarzSGS100A",
        "name": "SGSA100",
        "address": "TCPIP0::192.168.1.201::inst0::INSTR",
        "variables": {
            "frequency": bind_instrument_qubit("drive_frequency", "q0"),
            "power": bind_instrument_qubit("drive_power", "q0"),
        },
    },
    "yoko0": {
        "type": "CS",
        "model": "Yokogawa_GS200",
        "address": "TCPIP0::192.168.1.199::inst0::INSTR",
        "name": "yoko0",
        "ramp_step": 1e-6,
        "ramp_step_delay": 0.008,
        "current_range": 10e-3,  # Change when at 0 flux
        "variables": {"current": bind_instrument_qubit("current", "q0")},
    },
    "vna": {
        "type": "VNA",
        "model": "RohdeSchwarzZNA26",
        "name": "vna",
        "address": "TCPIP0::192.168.1.203::inst0::INSTR",
        "s_param": "S21",
        "variables": {
            "power": bind_instrument_qubit("readout_power", "q0"),
            "bandwidth": bind_instrument_qubit("readout_acquire_bandwith", "q0"),
            "averages": bind_instrument_qubit("readout_acquire_averages", "q0"),
        },
    },
}
