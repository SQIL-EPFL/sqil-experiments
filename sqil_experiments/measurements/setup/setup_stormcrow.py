import os

from helpers.laboneq import print_qpu_signals
from helpers.sqil_transmon.operations import SqilTransmonOperations
from helpers.sqil_transmon.qubit import SqilTransmon
from laboneq import serializers
from laboneq.contrib.example_helpers.generate_descriptor import generate_descriptor
from laboneq.contrib.example_helpers.generate_device_setup import (
    create_connection,
    generate_device_setup,
)
from laboneq.dsl.quantum import QPU
from laboneq.simple import DeviceSetup
from laboneq_applications.qpu_types.tunable_transmon import (
    TunableTransmonOperations,
    TunableTransmonQubit,
)
from sqil_core.experiment import bind_instrument_qubit

from sqil_experiments.qpu.sqil_transmon.operations import SqilTransmonOperations
from sqil_experiments.qpu.sqil_transmon.qubit import SqilTransmon

# Checklist for every cooldown
# - update data_folder_name
# - update the initial_readout_lo_freq, an approximate value is required to run onetone
data_folder_name = "20251110_stormcrow_N17"
initial_readout_lo_freq = 7.2e9


# Data storage
db_root = r"Z:\Projects\Stormcrow\data"
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
        number_qubits=1,
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
                "readout_lo_frequency": initial_readout_lo_freq,
                "drive_lo_frequency": 5e9,
                "aux_lo_frequency": 7e9,
            }
        )
    return qpu


instruments = {
    "zi": {
        "type": "ZI",
        "address": "localhost",
        # "descriptor": zi_descriptor,
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
