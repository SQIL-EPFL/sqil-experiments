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
from helpers.TD_setup_left_line_SGS import sgsa  # Rohde_Schwarz SGS100A
from helpers.TD_setup_left_line_SGS import db_path, descriptor_file, main_descriptor
from helpers.utilities import (
    analyze_qspec,
    external_average_loop,
    sparameter_to_dB_phase,
)
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from pulsed_twotone_vs_qu_power_SGS_exp import main_exp, setup_file
from tqdm import tqdm

sys.path.append("../TD_analyze")
from spectroscopy_2D_plot import spectroscopy_2D_plot

exp_name = "twotone_vs_qu_power"
tags = ["0_two tone vs qu power", "SGS"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7558000000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pulse_length": 5e-6,
    "sgsa_freq_start": 6.252e9,
    "sgsa_freq_stop": 6.254e9,
    "sgsa_freq_npts": 101,
    "qu_power_range": 0.4,  # 400mV. Should not exceed 0.5 in total voltage!!!
    "qu_pulse_amp": 0.95,  # better not exceed 0.95 (causing overload on HDAWG)
    "sgsa_power_start": 8,
    "sgsa_power_stop": 8,
    "sgsa_power_npts": 1,  # 8
    "reset_delay": 1e-6,  # [sec]
    "avg": 2**13,
    "external_avg": 1,
    "save_pulsesheet": False,
    "plot_fit": False,
    "plot_2D": False,
    "save_2D_plot": False,
}

qu_freq_sweep = np.linspace(
    param_dict["sgsa_freq_start"],
    param_dict["sgsa_freq_stop"],
    param_dict["sgsa_freq_npts"],
)
sgsa_power_sweep = np.linspace(
    param_dict["sgsa_power_start"],
    param_dict["sgsa_power_stop"],
    param_dict["sgsa_power_npts"],
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    qu_freq=dict(unit="Hz"),
    sgsa_power=dict(unit="dBm"),
    data=dict(axes=["qu_freq", "sgsa_power"], unit=""),
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
            f"{writer.filepath.parent}/qu_power_{qu_power}dBm_pulsesheet",
            compiled_exp,
            interactive=False,
        )

    sgsa.on()
    # qu_power sweep
    for sgsa_power in sgsa_power_sweep:
        specdata = np.array([])
        sgsa.power(sgsa_power)
        for qu_freq in tqdm(qu_freq_sweep):
            sgsa.frequency(qu_freq)
            # run the experiment and take external averages
            data = external_average_loop(
                session, compiled_exp, param_dict["external_avg"]
            )

            # save the data in DDH5 file
            writer.add_data(
                qu_freq=qu_freq,
                sgsa_power=sgsa_power,
                data=data,
            )
            specdata = np.append(specdata, data)

        # fit the data
        if param_dict["sgsa_power_npts"] == 1 and param_dict["plot_fit"] == True:

            f_0, fig_fit = analyze_qspec(
                specdata,
                qu_freq_sweep,
                f0=6.25e9,  # starting point
                a=1.0,
                gamma=2e6,
                rotate=True,
                flip=True,
            )
            fig_fit.suptitle(f"Qubit Power: {sgsa_power}dBm")
            fig_fit.savefig(
                f"{writer.filepath.parent}/sgsa_power_{sgsa_power}dBm_fit.png",
                bbox_inches="tight",
            )
            writer.save_text(
                f"fitted_qubit_freq_at_sgsa_power_{sgsa_power}dBm.md",
                f"fitted_qubit_freq:{f_0} Hz",
            )

    filepath_parent = writer.filepath.parent
sgsa.off()
sgsa.close()

if param_dict["plot_2D"] == True and param_dict["qu_power_npts"] > 1:
    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    qu_freq = h5file["data"]["qu_freq"][0][:]
    qu_power = h5file["data"]["qu_power"][:]
    data = h5file["data"]["data"][:][:]
    fig_2D_plot = spectroscopy_2D_plot(
        qu_freq,
        qu_power,
        data,
        "Qubit Frequency [GHz]",
        "Qubit Power [dBm]",
        "Mag [dBm]",
    )
    if param_dict["save_2D_plot"] == True:
        fig_2D_plot.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches="tight")
