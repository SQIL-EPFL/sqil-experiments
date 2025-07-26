from laboneq.contrib.example_helpers.generate_descriptor import generate_descriptor
from laboneq.simple import *

descriptor = generate_descriptor(
    pqsc=["DEV10190"],
    hdawg_8=["DEV9000"],
    shfqc_6=["DEV12422"],
    number_data_qubits=1,
    number_flux_lines=1,
    include_cr_lines=False,
    multiplex=False,
    number_multiplex=0,
    get_zsync=True,
    ip_address="localhost",
)

setup_generated = DeviceSetup.from_descriptor(descriptor)
print(setup_generated.to_json())
