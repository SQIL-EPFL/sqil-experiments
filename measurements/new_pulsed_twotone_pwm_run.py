import matplotlib.pyplot as plt
import numpy as np
from helpers.qubit_righttransmon_legacy import create_qubit_from_param_dict
from helpers.TD_setup_righttransmon import db_path, descriptor_file
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from pulsed_twotone_pwm_exp import main_exp, setup_file

from measurements.helpers.utils import external_average_loop

exp_name = "twotone_pwm"
tags = ["0_two tone pwm"]

param_dict = {
    "ro_pulse_length": 3e-6,
    "ro_freq": 7557906800,
    "ro_lo_freq": 7.3e9,
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pulse_length": 2000e-9,
    "qu_freq_start": 6.215e9,
    "qu_freq_stop": 6.225e9,
    "qu_freq_npts": 501,
    "qu_lo_freq": 5.9e9,
    "qu_drive_power": -20,
    "qu_drive_pwm_freq": 0e6,
    "reset_delay": 1e-6,
    "external_avg": 1,
    "plot_fit": True,
    "save_pulsesheet": True,
}

qubit, settings = create_qubit_from_param_dict(param_dict)

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
        from measurements.helpers.utils import analyze_qspec

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
