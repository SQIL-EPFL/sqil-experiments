from laboneq import serializers
from laboneq.contrib.example_helpers.generate_descriptor import generate_descriptor
from laboneq.dsl.quantum import QPU
from laboneq.simple import DeviceSetup
from laboneq_applications.qpu_types.tunable_transmon import (
    TunableTransmonOperations,
    TunableTransmonQubit,
)

from helpers.laboneq import print_qpu_signals

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
zi_setup = DeviceSetup.from_descriptor(zi_descriptor, "localhost")

# Instruments
instruments = {"zi_session": {"type": "ZI", "setup_obj": zi_setup}}


# Initialize QPU
# qubits = TunableTransmonQubit.from_device_setup(zi_setup)
# quantum_operations = TunableTransmonOperations()
# qpu = QPU(qubits=qubits, quantum_operations=quantum_operations)

# # Save QPU to file
# serializers.save(qpu, "qpu_test.json")
