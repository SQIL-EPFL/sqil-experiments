"""
Setup example to use Zurich Instruments emulation mode.
"""

import os

from laboneq_applications.qpu_types.tunable_transmon import demo_platform

# TODO: update cooldown name
data_folder_name = "my_emulation"
n_qubits = 2

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
    qt_platform = demo_platform(n_qubits=n_qubits)
    return qt_platform.setup


# QPU from demo platform
def generate_qpu(zi_setup):
    qt_platform = demo_platform(n_qubits=n_qubits)
    return qt_platform.qpu


instruments = {
    "zi": {
        "type": "ZI",
        "address": "localhost",
        "generate_setup": generate_zi_setup,
        "generate_qpu": generate_qpu,
    },
}
