import os
import sys

import h5py
import matplotlib.pyplot as plt
import numpy as np
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop, logsweep
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

sys.path.append("../analysis_code")
from inspection import inspect_decaying_oscillations
from ramsey_fringe_exp import main_exp, setup_file
from spectroscopy_2D_plot import spectroscopy_2D_plot

exp_name = "0_Ramsey_vs_ro_power"
tags = ["0_Ramsey", "T2_star", "TD"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7558600000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    # qubit1
    # "qu_pi_pulse_length":56e-9,
    # "qu_freq":6232417192,
    # "qu_lo_freq":5.8e9,
    # "qu_drive_power": 9.312,
    # "qu_freq_detune":200000,
    # "qu_freq_detune_npts": 41,
    # qubit2
    "qu_pi_pulse_length": 56e-9,
    "qu_freq": 6719050276,
    "qu_lo_freq": 6.3e9,
    "qu_drive_power": 8.298002409626068,
    "qu_freq_detune": 200e3,
    "qu_freq_detune_npts": 21,
    "interval_sweep_start": 1e-10,
    "interval_sweep_stop": 35e-6,
    "interval_sweep_npts": 35,
    "readout_delay": 0e-9,  # time interval between pulse sequence and the readout
    "reset_delay": 60e-6,  # [sec]
    "avg": 2**15,  # 2**17,
    "external_avg": 1,  # 4
    "save_pulsesheet": True,
    "plot_2D": True,
}

interval_sweep = np.linspace(
    param_dict["interval_sweep_start"],
    param_dict["interval_sweep_stop"],
    param_dict["interval_sweep_npts"],
)
qu_freq_sweep = np.linspace(
    param_dict["qu_freq"] - param_dict["qu_freq_detune"],
    param_dict["qu_freq"] + param_dict["qu_freq_detune"],
    param_dict["qu_freq_detune_npts"],
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    interval=dict(unit="sec"),
    qu_freq=dict(unit="Hz"),
    data=dict(axes=["interval", "qu_freq"]),
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
    # qu_freq sweep
    for qu_freq in qu_freq_sweep:
        exp = main_exp(session, param_dict, writer, qu_freq)
        compiled_exp = session.compile(exp)

        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/qu_freq_{qu_freq}_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        writer.add_data(interval=interval_sweep, qu_freq=qu_freq, data=data)

        if param_dict["qu_freq_detune_npts"] == 1:
            # plot and save the data and fitting
            inspect_decaying_oscillations(interval_sweep, data, figure=None)
            plt.savefig(
                f"{writer.filepath.parent}/qu_freq_{qu_freq}.png", bbox_inches="tight"
            )

        filepath_parent = writer.filepath.parent


if param_dict["qu_freq_detune_npts"] > 1 and param_dict["plot_2D"] == True:
    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    interval = h5file["data"]["interval"][0][:]
    qu_freq = h5file["data"]["qu_freq"][:]
    data = h5file["data"]["data"][:][:]
    fig_2D_plot, ax = spectroscopy_2D_plot(
        interval,
        qu_freq,
        data,
        "Interval [us]",
        "Qubit Freq [Hz]",
        "Mag [dB]",
        normalization=False,
    )
    fig_2D_plot.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches="tight")
