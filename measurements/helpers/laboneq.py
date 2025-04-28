from pprint import pprint

from laboneq.contrib.example_helpers.barebones.tunable_transmon import TunableTransmon


def get_physical_signal_name(setup, quid, signal_name):
    logical_signal = setup.logical_signal_groups[quid].logical_signals[signal_name]
    return logical_signal.physical_channel.uid


def print_qpu_signals(setup):
    qubit_signals = {
        quid: list(lsg.logical_signals)
        for quid, lsg in setup.logical_signal_groups.items()
    }
    connections = {
        quid: {
            sig_name: get_physical_signal_name(setup, quid, sig_name)
            for sig_name in signals
        }
        for quid, signals in qubit_signals.items()
    }

    pprint(connections)


class ExperimentSettings:
    def __init__(self):
        pass


def create_qubit_from_param_dict(
    param_dict: dict,
) -> tuple[TunableTransmon, ExperimentSettings]:
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
