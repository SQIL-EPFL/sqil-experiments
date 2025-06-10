from laboneq.contrib.example_helpers.initialize import initialize_laboneq
from laboneq.contrib.demo import demo_setup
import numpy as np

from time_rabi import create_experiment, TimeRabiOptions

initialize_laboneq()
session = demo_setup.create_demo_session()
qpu = demo_setup.create_demo_setup()
qubit = qpu.qubits[0]
pulse_lengths = np.linspace(0e-9, 300e-9, 31)
options = TimeRabiOptions(
    count=1024, transition="ge", averaging_mode="cyclic", acquisition_type="integration"
)

exp = create_experiment(
    qpu=qpu, qubit=qubit, pulse_lengths=pulse_lengths, options=options
)

compiled = session.compile(exp)

print("Experiment compiled successfully.")
