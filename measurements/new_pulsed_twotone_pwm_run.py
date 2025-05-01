from laboneq.simple import *
import numpy as np
import matplotlib.pyplot as plt

from helpers.qubit_righttransmon_legacy import create_qubit_from_param_dict
from helpers.TD_setup_righttransmon import db_path, descriptor_file
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from pulsed_twotone_pwm_exp import main_exp, setup_file
from helpers.utilities import external_average_loop

exp_name = "twotone_pwm"
tags = ["0_two tone pwm"]

qf = 5.3290e9

param_dict = {
    "ro_pulse_length": 3e-6,
    "ro_freq": 7.6174e9,
    "ro_lo_freq": 7.2e9,
    "ro_power": -30,
    "ro_acquire_range": -20,
    "qu_pulse_length": 2000e-9,
    "qu_freq_start": qf - 10e6,
    "qu_freq_stop": qf + 10e6,
    "qu_freq_npts": 101,
    "qu_lo_freq": 5.0e9,
    "qu_drive_power": -20,
    "qu_drive_pwm_freq": 0e6,
    "reset_delay": 1e-6,
    "external_avg": 1,
    "plot_fit": True,
    "save_pulsesheet": True,
}

# qubit, settings = create_qubit_from_param_dict(param_dict)


class ExperimentSettings:
    def __init__(self):
        pass


from laboneq.simple import *
from laboneq.contrib.example_helpers.generate_descriptor import generate_descriptor

zi_descriptor = generate_descriptor(
    shfqc_6=["dev12183"],
    number_data_qubits=1,
    number_flux_lines=0,
    include_cr_lines=False,
    multiplex=True,
    number_multiplex=1,
    get_zsync=False,
    ip_address="localhost",
)
zi_setup = DeviceSetup.from_descriptor(zi_descriptor, "localhost")

from laboneq_applications.qpu_types.tunable_transmon import (
    TunableTransmonQubit,
)

qubits = TunableTransmonQubit.from_device_setup(zi_setup)

qubits[0].parameters.drive_lo_frequency = 5e9
qubit = qubits[0]

settings = ExperimentSettings()
exp_keys = ["external_avg", "plot", "save", "fit", "pulsesheet", "write", "export"]

for key, value in param_dict.items():
    key_lower = key.lower()

    if any(sub in key_lower for sub in exp_keys):
        setattr(settings, key, value)
    else:
        setattr(qubit, key, value)

qu_freq_sweep = np.linspace(
    qubit.qu_freq_start,
    qubit.qu_freq_stop,
    qubit.qu_freq_npts,
)

datadict = DataDict(
    qu_freq=dict(unit="Hz"),
    data=dict(axes=["qu_freq"], unit=""),
)
datadict.validate()

with DDH5Writer(datadict, db_path, name=exp_name) as writer:
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, descriptor_file])

    device_setup = DeviceSetup.from_descriptor(descriptor_file)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)

    exp = main_exp(session, qubit, settings, writer)
    compiled_exp = session.compile(exp)

    if settings.save_pulsesheet:
        show_pulse_sheet(
            f"{writer.filepath.parent}/qu_pulsesheet", compiled_exp, interactive=False
        )

    data = external_average_loop(session, compiled_exp, settings.external_avg)

    writer.add_data(
        qu_freq=qu_freq_sweep,
        data=data,
    )

    if settings.plot_fit:
        from helpers.utilities import analyze_qspec

        f_0, fit_fig = analyze_qspec(
            data,
            qu_freq_sweep,
            f0=qu_freq_sweep[np.argmin(np.real(data))],
            a=1.0,
            gamma=2e6,
            rotate=True,
            flip=True,
        )
        fit_fig.savefig(f"{writer.filepath.parent}/qu_fit.png", bbox_inches="tight")
        writer.save_text(f"fitted_qubit_freq.md", f"fitted_qubit_freq:{f_0} Hz")

    plt.figure()
    plt.plot(qu_freq_sweep * 1e-9, 20 * np.log10(np.abs(data)))
    plt.xlabel("qubit_drive_lo_freq + qubit_drive_if_freq [GHz]")
    plt.ylabel("Magnitude [dB]")
    plt.title("Modulation frequency: " + str(qubit.qu_drive_pwm_freq))
    plt.legend()
    plt.savefig(f"{writer.filepath.parent}/mag.png", bbox_inches="tight")
