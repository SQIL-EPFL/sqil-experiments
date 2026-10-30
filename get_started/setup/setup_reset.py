"""
One-qubit setup with a reset tone on SG channel 2 (device 5 = q0).
Copy of setup_mux.py with:
- n_qubits = 1 (q0 drive on SG channel 1, readout on the QA channel)
- an aux line "q0/aux" on SG channel 2 for the reset tone
  (same mechanism as the aux line in get_started/setup/setup_stormcrow.py)
- the drive in LF mode: SG1 and SG2 share one synthesizer in RF mode, so the
  drive (~100 MHz) goes through the LF path and the synthesizer is free for
  the reset tone on SG2 (~7 GHz, RF path)
- its own QPU file (qpu_reset_ar.json)
"""

import os

from laboneq.contrib.example_helpers.generate_device_setup import (
    create_connection,
    generate_device_setup,
)
from laboneq.dsl.quantum import QPU
from laboneq.simple import Calibration, PortMode, SignalCalibration
from sqil_core.experiment import bind_instrument_qubit

from sqil_experiments.qpu.sqil_transmon.operations import SqilTransmonOperations
from sqil_experiments.qpu.sqil_transmon.qubit import SqilTransmon

n_qubits = 1

data_folder_name = "20261210_20251110_Fluxonoim_AQUA"

# Data storage
db_root = r"Z:\Projects\Transmon\multiplexed"
db_root_local = r"C:\Users\sqil\Desktop\data_local"
storage = {
    "db_type": "plottr",
    "db_path": os.path.join(db_root, data_folder_name),
    "db_path_local": os.path.join(db_root_local, data_folder_name),
    "qpu_filename": "qpu_reset_ar.json",
}


# Zurich Instruments setup
def generate_zi_setup():
    setup = generate_device_setup(
        number_qubits=n_qubits,
        shfqc=[
            {
                "serial": "dev12537",
                "number_of_channels": 2,
                "options": "SHFQC/LRT/PLUS/QC2CH",
            }
        ],
        include_flux_lines=False,
        multiplex_drive_lines=True,
        query_options=False,
    )

    # Reset tone: aux line on SG channel 2 (index 1)
    conn = create_connection(to_signal="q0/aux", ports="SGCHANNELS/1/OUTPUT")
    setup.add_connections("shfqc_0", conn)

    # Drive (SG channel 1) through the LF path
    setup.set_calibration(
        Calibration(
            {
                setup.logical_signal_by_uid("q0/drive"): SignalCalibration(
                    port_mode=PortMode.LF
                ),
                setup.logical_signal_by_uid("q0/drive_ef"): SignalCalibration(
                    port_mode=PortMode.LF
                ),
            }
        )
    )
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
                "drive_lo_frequency": 100e6,  # LF path: multiples of 100 MHz
                "drive_range": 5,  # LF path: max +5 dBm
                "aux_lo_frequency": 7e9,  # RF path: multiples of 200 MHz
            }
        )
    return qpu


instruments = {
    "yoko0": {
        "type": "CS",
        "model": "Yokogawa_GS200",
        "address": "TCPIP0::192.168.1.51::inst0::INSTR",
        "name": "yoko0",
        "ramp_step": 1e-6,
        "ramp_step_delay": 0.008,
        "current_range": 1e-3,  # Change when at 0 flux
        "variables": {"current": bind_instrument_qubit("current", "q0")},
    },
    "zi": {
        "type": "ZI",
        "address": "localhost",
        "generate_setup": generate_zi_setup,
        "generate_qpu": generate_qpu,
    },
}
