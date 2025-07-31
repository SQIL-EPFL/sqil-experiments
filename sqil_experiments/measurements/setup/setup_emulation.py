import os

from helpers.laboneq import print_qpu_signals
from helpers.sqil_transmon.operations import SqilTransmonOperations
from helpers.sqil_transmon.qubit import SqilTransmon
from laboneq import serializers
from laboneq.contrib.example_helpers.generate_descriptor import generate_descriptor
from laboneq.contrib.example_helpers.generate_device_setup import generate_device_setup
from laboneq.dsl.quantum import QPU
from laboneq.simple import DeviceSetup
from laboneq_applications.qpu_types.tunable_transmon import (
    TunableTransmonOperations,
    TunableTransmonQubit,
    demo_platform,
)
from sqil_core.experiment import bind_instrument_qubit

n_qubit = 2

data_folder_name = "emulation"

# Data storage
db_root = r"Z:\Projects\BottomLoader\data"
db_root_local = r"./data_local/"
storage = {
    "db_type": "plottr",
    "db_path": os.path.join(db_root, data_folder_name),
    "db_path_local": os.path.join(db_root_local, data_folder_name),
    "qpu_filename": "qpu.json",
}


# Zurich Instruments setup
def generate_zi_setup():
    qt_platform = demo_platform(n_qubits=n_qubit)
    return qt_platform.setup


# zi_setup = DeviceSetup.from_descriptor(zi_descriptor, "localhost")
def generate_qpu(zi_setup):
    qt_platform = demo_platform(n_qubits=n_qubit)
    return qt_platform.qpu


instruments = {
    # "sgs": {
    #     "type": "LO",
    #     "model": "RohdeSchwarzSGS100A",
    #     "name": "SGSA100",
    #     "address": "TCPIP0::192.168.1.56::inst0::INSTR",
    #     # "connect": lambda self, *args, **kwargs: print("CUSTOM CONNECT TO", self.name),
    #     "setup": setup_lo,
    #     "variables": {
    #         "frequency": lambda exp: (
    #             exp.qpu.quantum_elements[0].parameters.external_lo_frequency
    #         ),
    #         "power": lambda exp: (
    #             exp.qpu.quantum_elements[0].parameters.external_lo_power
    #         ),
    #     },
    # },
    "zi": {
        "type": "ZI",
        "address": "localhost",
        # "descriptor": zi_descriptor,
        "generate_setup": generate_zi_setup,
        "generate_qpu": generate_qpu,
    },
    # "yoko0": {
    #     "type": "CS",
    #     "model": "Yokogawa_GS200",
    #     "address": "TCPIP0::192.168.1.199::inst0::INSTR",
    #     "name": "yoko0",
    #     "variables": {
    #         #      "current": lambda exp: (exp.qpu.quantum_elements[0].parameters.current),
    #         "current": bind_instrument_qubit("current", "q0")
    #     },
    # },
}

# Initialize QPU
# qubits = TunableTransmonQubit.from_device_setup(zi_setup)
# quantum_operations = TunableTransmonOperations()
# qpu = QPU(qubits=qubits, quantum_operations=quantum_operations)

# # Save QPU to file
# serializers.save(qpu, "qpu_test.json")
