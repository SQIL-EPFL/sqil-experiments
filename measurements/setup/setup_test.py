from laboneq import serializers
from laboneq.contrib.example_helpers.generate_descriptor import generate_descriptor
from laboneq.dsl.quantum import QPU
from laboneq.simple import DeviceSetup
from laboneq_applications.qpu_types.tunable_transmon import (
    TunableTransmonOperations,
    TunableTransmonQubit,
)

from helpers.laboneq import print_qpu_signals

from helpers.sqil_transmon.qubit import SqilTransmon
from helpers.sqil_transmon.operations import SqilTransmonOperations


# Zurich instruments stetup
zi_descriptor = generate_descriptor(
    shfqc_6=["dev12183"],
    number_data_qubits=1,
    number_flux_lines=0,
    include_cr_lines=False,
    multiplex=True,
    number_multiplex=1,
    get_zsync=False,
    ip_address="localhost",
)


# zi_setup = DeviceSetup.from_descriptor(zi_descriptor, "localhost")
def get_qpu(zi_setup):
    qubits = SqilTransmon.from_device_setup(zi_setup)
    quantum_operations = SqilTransmonOperations()
    qpu = QPU(qubits=qubits, quantum_operations=quantum_operations)
    return qpu


# Instruments
instruments = {
    "sgs": {
        "type": "LO",
        "model": "RohdeSchwarzSGS100A",
        "name": "SGSA100",
        "address": "TCPIP0::192.168.1.201::inst0::INSTR",
        # "connect": lambda self, *args, **kwargs: print("CUSTOM CONNECT TO", self.name),
    },
    "zi": {
        "type": "ZI",
        "address": "localhost",
        "descriptor": zi_descriptor,
        "get_qpu": get_qpu,
    },
}

# Data storage
storage = {
    "db_type": "plottr",
    "db_path": r"C:\Users\sqil\Desktop\code\sqil-experiments\measurements\data",
    "db_path_local": r"C:\Users\sqil\Desktop\code\sqil-experiments\measurements\data_local",
}


# Initialize QPU
# qubits = TunableTransmonQubit.from_device_setup(zi_setup)
# quantum_operations = TunableTransmonOperations()
# qpu = QPU(qubits=qubits, quantum_operations=quantum_operations)

# # Save QPU to file
# serializers.save(qpu, "qpu_test.json")
