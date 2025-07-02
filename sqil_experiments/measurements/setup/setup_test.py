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
)

# Checklist for every cooldown
# - update data_folder_name
# - update the initial_readout_lo_freq, an approximate value is required to run onetone
data_folder_name = "test"
initial_readout_lo_freq = 7.2e9


# Data storage
db_root = r"Z:\Projects\BottomLoader\data"
db_root_local = r"C:\Users\sqil\Desktop\code\sqil-experiments\data_local"
storage = {
    "db_type": "plottr",
    "db_path": os.path.join(db_root, data_folder_name),
    "db_path_local": os.path.join(db_root_local, data_folder_name),
    "qpu_filename": "qpu.json",
}


# Zurich instruments setup from descriptor
# Requires laboneq < 2.51 - generate_descriptor doesn't support
# passing instrument options, like "SHFQC/QC4CH" which are now mandatory
zi_descriptor = generate_descriptor(
    shfqc_6=["dev12183"],
    number_data_qubits=1,
    number_flux_lines=0,
    include_cr_lines=False,
    multiplex=False,
    number_multiplex=0,
    get_zsync=False,
    ip_address="localhost",
)
# zi_setup = DeviceSetup.from_descriptor(zi_descriptor, "localhost")


# Zurich Instruments setup
def generate_zi_setup():
    return generate_device_setup(
        number_qubits=1,
        shfqc=[
            {"serial": "dev12183", "number_of_channels": 4, "options": "SHFQC/QC4CH"}
        ],
        include_flux_lines=False,
        multiplex_drive_lines=True,
        query_options=False,
    )


# zi_setup = DeviceSetup.from_descriptor(zi_descriptor, "localhost")
def generate_qpu(zi_setup):
    qubits = SqilTransmon.from_device_setup(zi_setup)
    quantum_operations = SqilTransmonOperations()
    qpu = QPU(qubits, quantum_operations)

    # Set required qubit parameters
    for qubit in qpu.quantum_elements:
        qubit.update(
            **{
                "readout_lo_frequency": initial_readout_lo_freq,
                "drive_lo_frequency": 5e9,
            }
        )
    return qpu


# Instruments
def setup_lo(self, *args, **kwargs):
    self.set_frequency(11e9)
    self.set_power(-20)


instruments = {
    "sgs": {
        "type": "LO",
        "model": "RohdeSchwarzSGS100A",
        "name": "SGSA100",
        "address": "TCPIP0::192.168.1.56::inst0::INSTR",
        # "connect": lambda self, *args, **kwargs: print("CUSTOM CONNECT TO", self.name),
        "setup": setup_lo,
        "variables": {
            "frequency": lambda exp: (
                exp.qpu.quantum_elements[0].parameters.external_lo_frequency
            ),
            "power": lambda exp: (
                exp.qpu.quantum_elements[0].parameters.external_lo_power
            ),
        },
    },
    "zi": {
        "type": "ZI",
        "address": "localhost",
        # "descriptor": zi_descriptor,
        "generate_setup": generate_zi_setup,
        "generate_qpu": generate_qpu,
    },
}

# Initialize QPU
# qubits = TunableTransmonQubit.from_device_setup(zi_setup)
# quantum_operations = TunableTransmonOperations()
# qpu = QPU(qubits=qubits, quantum_operations=quantum_operations)

# # Save QPU to file
# serializers.save(qpu, "qpu_test.json")
