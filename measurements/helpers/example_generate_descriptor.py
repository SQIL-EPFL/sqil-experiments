from laboneq.simple import *
from laboneq.contrib.example_helpers.generate_descriptor import generate_descriptor

descriptor = generate_descriptor(
    shfqc_6=["dev12183"],
    number_data_qubits=1,
    number_flux_lines=0,
    include_cr_lines=False,
    multiplex=True,
    number_multiplex=1,
    get_zsync=False,
    ip_address="localhost",
)

setup_generated = DeviceSetup.from_descriptor(descriptor)
print(setup_generated.to_json())
