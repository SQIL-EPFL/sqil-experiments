from laboneq_applications.qpu_types.tunable_transmon import TunableTransmonQubit


class ExperimentSettings:
    def __init__(self):
        pass


def create_qubit_from_param_dict(
    param_dict: dict,
) -> tuple[TunableTransmonQubit, ExperimentSettings]:
    qubit = TunableTransmonQubit(uid="q0")
    settings = ExperimentSettings()

    exp_keys = ["external_avg", "plot", "save", "fit", "pulsesheet", "write", "export"]

    for key, value in param_dict.items():
        key_lower = key.lower()

        if any(sub in key_lower for sub in exp_keys):
            setattr(settings, key, value)
        else:
            setattr(qubit, key, value)

    return qubit, settings
