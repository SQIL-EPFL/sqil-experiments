"""
Setup example for the first iteration of Stormcrow devices.
See how to connect an HDAWG, PSQSC, and how to map additional SHFQC channels
to have an auxiliary (aux) drive.
"""

import os

from laboneq.contrib.example_helpers.generate_device_setup import (
    create_connection,
    generate_device_setup,
)
from laboneq.dsl.quantum import QPU
from sqil_core.experiment import bind_instrument_qubit

from sqil_experiments.qpu.sqil_transmon.operations import SqilTransmonOperations
from sqil_experiments.qpu.sqil_transmon.qubit import SqilTransmon

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


# Zurich Instruments setup
def generate_zi_setup():
    setup = generate_device_setup(
        number_qubits=n_qubits,
        shfqc=[
            {"serial": "dev12183", "number_of_channels": 4, "options": "SHFQC/QC4CH"}
            # { "serial": "dev12537", "number_of_channels": 4, "options": "SHFQC/PLUS/QC2CH" }
        ],
        pqsc=[{"serial": "dev10218"}],
        hdawg=[{"serial": "dev9131", "options": "HDAWG8"}],
        include_flux_lines=False,
        multiplex_drive_lines=True,
    )

    # Create an additional aux channel
    conn = create_connection(to_signal=f"q0/aux", ports="SGCHANNELS/2/OUTPUT")
    setup.add_connections(f"shfqc_0", conn)

    # Connect to HDAWG channel
    conn = create_connection(to_signal=f"q0/hdawg", ports="SIGOUTS/0")
    setup.add_connections("hdawg_0", conn)

    return setup


def generate_qpu(zi_setup):
    qubits = SqilTransmon.from_device_setup(zi_setup)
    quantum_operations = SqilTransmonOperations()
    qpu = QPU(qubits, quantum_operations)

    # Set required qubit parameters
    for qubit in qpu.quantum_elements:
        qubit.update(
            **{
                "readout_lo_frequency": 7e9,
                "drive_lo_frequency": 5e9,
                "aux_lo_frequency": 7e9,
                "readout_configuration": "transmission",
            }
        )
    return qpu


instruments = {
    "zi": {
        "type": "ZI",
        "address": "localhost",
        "generate_setup": generate_zi_setup,
        "generate_qpu": generate_qpu,
    },
    "yoko0": {
        "type": "CS",
        "model": "Yokogawa_GS200",
        "address": "TCPIP0::192.168.1.201::inst0::INSTR",
        "name": "yoko0",
        "ramp_step": 1e-6,
        "ramp_step_delay": 0.008,
        "current_range": 10e-3,  # Change when at 0 flux
        "variables": {"current": bind_instrument_qubit("current", "q0")},
    },
}
