from pprint import pprint

from laboneq_applications.qpu_types.tunable_transmon import TunableTransmonQubit
from .utils import shfqa_power_calculator


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
) -> tuple[TunableTransmonQubit, ExperimentSettings]:
    qubit = TunableTransmonQubit(
        name="q0",
        readout_amplitude=1.0,
        drive_amplitude=1.0,
        port_delay=0,
    )
    settings = ExperimentSettings()

    exp_keys = [
        "external_avg",
        "avg",
        "plot",
        "save",
        "fit",
        "pulsesheet",
        "write",
        "export",
    ]

    for key, value in param_dict.items():
        key_lower = key.lower()

        if any(sub in key_lower for sub in exp_keys):
            setattr(settings, key, value)
        else:
            setattr(qubit, key, value)

    return qubit, settings


map_dict_to_transmon = {
    "ro_freq": "readout_resonator_frequency",
    "ro_lo_freq": "readout_lo_frequency",
    "ro_pulse_length": "readout_length",
    # "ro_power_range": "readout_range_out",
    "qu_lo_freq": "drive_lo_frequency",
    # "qu_pi_pulse_length": "ge_drive_length",
}

required_fields = [
    "readout_lo_frequency",
    "readout_resonator_frequency",
    "drive_lo_frequency",
]


def param_dict_to_tunable_transmon(
    qubit: TunableTransmonQubit, dict: dict
) -> TunableTransmonQubit:
    # ro_power, ro_acquire_range, ro_power_amp, qu_freq
    for key, value in map_dict_to_transmon.items():
        setattr(qubit.parameters, value, dict[key])

    ro_power_range, ro_signal_amp = shfqa_power_calculator(dict["ro_power"])
    qubit.parameters.readout_range_out = ro_power_range
    qubit.parameters.readout_amplitude = ro_signal_amp

    qu_power_range, qu_signal_amp = shfqa_power_calculator(dict["qu_power"])
    qubit.parameters.drive_range = qu_power_range
    return qubit
