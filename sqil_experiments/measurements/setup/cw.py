import os

from laboneq.dsl.quantum import QPU
from laboneq_applications.qpu_types.tunable_transmon import demo_platform
from sqil_core.experiment import bind_instrument_qubit

from sqil_experiments.measurements.helpers.sqil_transmon.operations import (
    SqilTransmonOperations,
)
from sqil_experiments.measurements.helpers.sqil_transmon.qubit import SqilTransmon

n_qubit = 1

# Checklist for every cooldown
# - update data_folder_name
# - update the initial_readout_lo_freq, an approximate value is required to run onetone
data_folder_name = "20251001_stormcrow_N17"
initial_readout_lo_freq = 7.2e9


# Data storage
db_root = r"Z:\Projects\BottomLoader\data"
db_root_local = r"C:\Users\sqil\Desktop\data_local"
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
instruments = {
    "q0_drive": {
        "type": "RF",
        "model": "RohdeSchwarzSGS100A",
        "name": "SGSA100",
        "address": "TCPIP0::192.168.1.201::inst0::INSTR",
        "variables": {
            "frequency": lambda exp: (
                exp.qpu.quantum_elements[0].parameters.readout_external_lo_frequency
            ),
            "power": lambda exp: (
                exp.qpu.quantum_elements[0].parameters.readout_external_lo_power
            ),
        },
    },
    "zi": {
        "type": "ZI",
        "address": "localhost",
        "generate_setup": generate_zi_setup,
        "generate_qpu": generate_qpu,
    },
    "yoko0": {
        "type": "CS",
        "model": "Yokogawa_GS200",
        "address": "TCPIP0::192.168.1.199::inst0::INSTR",
        "name": "yoko0",
        "variables": {"current": bind_instrument_qubit("current", "q0")},
    },
    "vna": {
        "type": "VNA",
        "model": "RohdeSchwarzZNA26",
        "name": "vna",
        "address": "TCPIP0::192.168.1.203::inst0::INSTR",
        "s_param": "S21",
        "variables": {"power": bind_instrument_qubit("cw_ro_power", "q0")},
    },
}
