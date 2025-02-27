"""
measurement code for pulsed-twotone 

Equipment:
    ZI SHFQC for readout
    ZI SHFQC for qubit drive
"""

import os
import sys

import h5py
import matplotlib.pyplot as plt
import numpy as np
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import (
    analyze_qspec,
    external_average_loop,
    sparameter_to_dB_phase,
)
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from pulsed_twotone_vs_ro_power_exp import main_exp, setup_file

sys.path.append("../analysis_code")
from spectroscopy_1D_plot import spectroscopy_1D_plot
from spectroscopy_2D_plot import spectroscopy_2D_plot

exp_name = "twotone_vs_ro_power"
tags = ["0_two tone vs ro power"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7568474709,
    "ro_lo_freq": 7.1e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power_start": -30,
    "ro_power_stop": -20,
    "ro_power_npts": 1,
    "ro_acquire_range": -5,
    # qubit2
    "qu_pulse_length": 10e-6,
    "qu_freq_start": 6.732e9,  # Q1: 6.250e9, #Q2: 6.737e9
    "qu_freq_stop": 6.738e9,  # Q1: 6.256e9, #Q2: 6.743e9
    "qu_freq_npts": 201,
    "qu_lo_freq": 6.3e9,
    "qu_drive_power": -50,
    "reset_delay": 0e-6,  # [sec]
    "avg": 2**15,
    "external_avg": 1,
    "save_pulsesheet": False,
    "plot_fit": True,
    "plot_2D": False,
    "save_2D_plot": False,
}

qu_freq_sweep = np.linspace(
    param_dict["qu_freq_start"], param_dict["qu_freq_stop"], param_dict["qu_freq_npts"]
)
ro_power_sweep = np.linspace(
    param_dict["ro_power_start"],
    param_dict["ro_power_stop"],
    param_dict["ro_power_npts"],
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    qu_freq=dict(unit="Hz"),
    ro_power=dict(unit="dBm"),
    data=dict(axes=["qu_freq", "ro_power"], unit=""),
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

    # ro_power sweep
    for ro_power in ro_power_sweep:
        exp = main_exp(session, param_dict, writer, ro_power)
        compiled_exp = session.compile(exp)

        # output and save a pulse sheet
        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/ro_power_{ro_power}dBm_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        # save the data in DDH5 file
        writer.add_data(
            qu_freq=qu_freq_sweep,
            ro_power=ro_power,
            data=data,
        )

        # fit the data
        if param_dict["ro_power_npts"] == 1 and param_dict["plot_fit"] == True:

            fig_fit, f0, fwhm = spectroscopy_1D_plot(
                qu_freq_sweep, data, xlabel="Qubit Frequency [GHz]", ylabel="Mag []"
            )
            qu_drive_power = param_dict["qu_drive_power"]
            fig_fit.suptitle(
                f"RO Power: {ro_power}dBm | Qubit Power: {qu_drive_power}dBm"
            )
            fig_fit.savefig(
                f"{writer.filepath.parent}/ro_power_{ro_power}dBm_fit.png",
                bbox_inches="tight",
            )
            writer.save_text(
                f"fitted_qubit_freq_at_ro_power_{ro_power}dBm.md",
                f"fitted_qubit_freq:{f0} Hz",
            )

    filepath_parent = writer.filepath.parent


if param_dict["plot_2D"] == True and param_dict["ro_power_npts"] > 1:
    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    qu_freq = h5file["data"]["qu_freq"][0][:]
    ro_power = h5file["data"]["ro_power"][:]
    data = h5file["data"]["data"][:][:]
    fig_2D_plot_mag = spectroscopy_2D_plot(
        qu_freq,
        ro_power,
        data,
        "Qubit Frequency [GHz]",
        "Readout Power [dBm]",
        "Mag [dBm]",
        normalization=True,
    )
    if param_dict["save_2D_plot"] == True:
        fig_2D_plot_mag.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches="tight")
