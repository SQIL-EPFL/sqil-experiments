"""
Equipment:
    ZI SHFQC for readout
    ZI SHFQC for qubit drive
"""

import matplotlib.pyplot as plt
import numpy as np
from dispersive_shift_pwm_exp import main_exp, setup_file
from helpers.TD_setup_righttransmon import db_path, descriptor_file, main_descriptor
from helpers.utilities import (
    analyze_qspec,
    external_average_loop_dispersive_ge,
    sparameter_to_dB_phase,
)
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

exp_name = "dispersive_shift_pwm"
tags = ["0_dispersive_shift_pwm"]

param_dict = {
    "ro_pulse_length": 3e-6,  # [sec]
    "ro_freq_start": 7.553e9,
    "ro_freq_stop": 7.560e9,
    "ro_freq_npts": 101,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pulse_length": 125e-9,
    "qu_freq": 6219934629,
    "qu_lo_freq": 6.0e9,
    "qu_drive_power": 9.55,
    "qu_drive_pwm_freq": 100e6,
    "reset_delay": 50e-6,  # [sec]
    "avg": 2**14,
    "external_avg": 1,
    "save_pulsesheet": True,
}

ro_freq_sweep = np.linspace(
    param_dict["ro_freq_start"], param_dict["ro_freq_stop"], param_dict["ro_freq_npts"]
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    ro_freq=dict(unit="Hz"),
    ground_data=dict(axes=["ro_freq"], unit=""),
    excited_data=dict(axes=["ro_freq"], unit=""),
)
datadict.validate()

with DDH5Writer(datadict, db_path, name=exp_name) as writer:
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, descriptor_file])
    writer.save_text("directry_path.md", f"{writer.filepath.parent}")

    # create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)

    exp = main_exp(session, param_dict, writer)
    compiled_exp = session.compile(exp)

    # output and save a pulse sheet
    if param_dict["save_pulsesheet"] == True:
        show_pulse_sheet(
            f"{writer.filepath.parent}/pulsesheet", compiled_exp, interactive=False
        )

    # run the experiment and take external averages
    data0, data1 = external_average_loop_dispersive_ge(
        session,
        compiled_exp,
        param_dict["external_avg"],
    )

    # save the data in DDH5 file
    writer.add_data(ro_freq=ro_freq_sweep, ground_data=data0, excited_data=data1)

    # plot magnitude (dB)
    plt.figure()
    plt.plot(
        ro_freq_sweep * 1e-9, 20 * np.log10(np.abs(data0)), label="ground", color="blue"
    )
    plt.plot(
        ro_freq_sweep * 1e-9, 20 * np.log10(np.abs(data1)), label="excited", color="red"
    )
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude [dB]")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_mag.png", bbox_inches="tight"
    )
    # plot magnitude difference(dB)
    plt.figure()
    plt.plot(
        ro_freq_sweep * 1e-9,
        20 * np.log10(np.abs(data0)) - 20 * np.log10(np.abs(data1)),
        label="g - e",
        color="green",
    )
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude [dB]")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_mag_difference.png",
        bbox_inches="tight",
    )

    # plot phase (rad)
    plt.figure()
    plt.plot(ro_freq_sweep * 1e-9, np.angle(data0), label="ground", color="blue")
    plt.plot(ro_freq_sweep * 1e-9, np.angle(data1), label="excited", color="red")
    plt.plot(
        ro_freq_sweep * 1e-9,
        np.angle(data0) - np.angle(data1),
        label="g - e",
        color="green",
    )
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Phase [rad]")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_phase.png", bbox_inches="tight"
    )

    # plot magnitude (dB)
    plt.figure()
    plt.plot(ro_freq_sweep * 1e-9, np.abs(data0), label="ground", color="blue")
    plt.plot(ro_freq_sweep * 1e-9, np.abs(data1), label="excited", color="red")
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude []")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_linmag.png", bbox_inches="tight"
    )
    # plot magnitude difference(dB)
    plt.figure()
    plt.plot(
        ro_freq_sweep * 1e-9,
        np.abs(data0) - np.abs(data1),
        label="g - e",
        color="green",
    )
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude []")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_linmag_difference.png",
        bbox_inches="tight",
    )
