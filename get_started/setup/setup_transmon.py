"""
Example of a setup with a single SHFQC for simple transmon measurements.
"""

import os

from laboneq.contrib.example_helpers.generate_device_setup import generate_device_setup
from laboneq.dsl.quantum import QPU

from sqil_experiments.qpu.sqil_transmon.operations import SqilTransmonOperations
from sqil_experiments.qpu.sqil_transmon.qubit import SqilTransmon

n_qubits = 1

# TODO: update cooldown name
data_folder_name = "my_cooldown"

# Data storage
db_root = r"Z:\Projects\BottomLoader\data"  # TODO: update database folder, e.g. Z:\Projects\...
db_root_local = r"C:\Users\sqil\Desktop\data_local"
storage = {
    "db_type": "plottr",
    "db_path": os.path.join(db_root, data_folder_name),
    "db_path_local": os.path.join(db_root_local, data_folder_name),
    "qpu_filename": "qpu.json",
}


# Zurich Instruments setup
def generate_zi_setup():
    return generate_device_setup(
        number_qubits=n_qubits,
        shfqc=[
            # {"serial": "dev12183", "number_of_channels": 4, "options": "SHFQC/QC4CH"}
            {
                "serial": "dev12537",
                "number_of_channels": 4,
                "options": "SHFQC/PLUS/QC2CH",
            }
        ],
        include_flux_lines=False,
        multiplex_drive_lines=True,
        query_options=False,
    )


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
}
