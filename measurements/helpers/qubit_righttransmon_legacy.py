from laboneq.contrib.example_helpers.barebones.tunable_transmon import TunableTransmon

class ExperimentSettings:
    def __init__(self):
        pass

def create_qubit_from_param_dict(param_dict: dict) -> tuple[TunableTransmon, ExperimentSettings]:
    qubit = TunableTransmon(
        name="q0",
        readout_amplitude=1.0,
        drive_amplitude=1.0,
        port_delay=0,
    )
    settings = ExperimentSettings()

    exp_keys = ["external_avg", "plot", "save", "fit", "pulsesheet", "write", "export"]

    for key, value in param_dict.items():
        key_lower = key.lower()

        if any(sub in key_lower for sub in exp_keys):
            setattr(settings, key, value)
        else:
            setattr(qubit, key, value)

    return qubit, settings
