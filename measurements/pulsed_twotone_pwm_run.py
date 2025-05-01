"""
measurement code for pulsed-twotone

Equipment:
    ZI SHFQC for readout
    ZI SHFQC for qubit drive
"""

import matplotlib.pyplot as plt
import numpy as np
from helpers.TD_setup_righttransmon import db_path, descriptor_file, main_descriptor
from helpers.utilities import (
    analyze_qspec,
    external_average_loop,
    sparameter_to_dB_phase,
)
from laboneq.simple import *
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from pulsed_twotone_pwm_exp import main_exp, setup_file

exp_name = "twotone_pwm"
tags = ["0_two tone pwm"]

param_dict = {
    "ro_pulse_length": 3e-6,  # [sec]
    "ro_freq": 7557906800,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pulse_length": 2000e-9,
    "qu_freq_start": 6.215e9,
    "qu_freq_stop": 6.225e9,
    "qu_freq_npts": 501,
    "qu_lo_freq": 5.9e9,
    "qu_drive_power": -20,
    "qu_drive_pwm_freq": 0e6,
    "reset_delay": 1e-6,  # [sec]
    "avg": 2**14,
    "external_avg": 1,
    "save_pulsesheet": True,
    "plot_fit": True,
}

qu_freq_sweep = np.linspace(
    param_dict["qu_freq_start"], param_dict["qu_freq_stop"], param_dict["qu_freq_npts"]
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    qu_freq=dict(unit="Hz"),
    data=dict(axes=["qu_freq"], unit=""),
)
datadict.validate()

with DDH5Writer(datadict, db_path, name=exp_name) as writer:
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, descriptor_file])

    # create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)

    exp = main_exp(session, param_dict, writer)
    compiled_exp = session.compile(exp)

    # output and save a pulse sheet
    if param_dict["save_pulsesheet"] == True:
        show_pulse_sheet(
            f"{writer.filepath.parent}/qu_pulsesheet", compiled_exp, interactive=False
        )

    # run the experiment and take external averages
    data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

    # save the data in DDH5 file
    writer.add_data(
        qu_freq=qu_freq_sweep,
        data=data,
    )

    # fit the data
    if param_dict["plot_fit"] == True:
        f_0, fit_fig = analyze_qspec(
            data,
            qu_freq_sweep,
            f0=qu_freq_sweep[np.argmin(np.real(data))],  # starting point
            a=1.0,
            gamma=2e6,
            rotate=True,
            flip=True,
        )
        fit_fig.savefig(f"{writer.filepath.parent}/qu_fit.png", bbox_inches="tight")
        writer.save_text(f"fitted_qubit_freq.md", f"fitted_qubit_freq:{f_0} Hz")

    # plot magnitude (dB)
    plt.figure()
    plt.plot(qu_freq_sweep * 1e-9, 20 * np.log10(np.abs(data)))
    plt.xlabel("qubit_drive_lo_freq + qubit_drive_if_freq [GHz]")
    plt.ylabel("Magnitude [dB]")
    plt.title("Modulation frequency: " + str(param_dict["qu_drive_pwm_freq"]))
    plt.legend()
    plt.savefig(f"{writer.filepath.parent}/mag.png", bbox_inches="tight")
