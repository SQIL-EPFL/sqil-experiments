import sys

import matplotlib.pyplot as plt
import numpy as np
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from tqdm import tqdm

sys.path.append("../analysis_code")
from amp_rabi_exp import main_exp, setup_file
from inspection import inspect_decaying_oscillations_amprabi

exp_name = "amp_rabi"
tags = ["0_amp rabi"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7568474709,
    "ro_lo_freq": 7.1e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    # qubit1
    "qu_pulse_length": 64e-9,
    "qu_freq": 6238372448,
    "qu_lo_freq": 5.8e9,
    "qu_power_range": 10,
    "qu_pulse_amp_start": 0.0,
    "qu_pulse_amp_stop": 1,
    "qu_pulse_amp_npts": 101,
    # qubit2
    # "qu_pulse_length":56e-9,
    # "qu_freq":6719050276,
    # "qu_lo_freq":6.3e9,
    # "qu_power_range": 10,
    # "qu_pulse_amp_start":0.0,
    # "qu_pulse_amp_stop":0.95,
    # "qu_pulse_amp_npts":21,
    "reset_delay": 60e-6,  # [sec]
    "avg": 2**15,
    "external_avg": 1,
    "save_pulsesheet": False,
    "sweep": False,  # str. name of the parameter in param_dict
    "sweep_start": None,
    "sweep_stop": None,
    "sweep_npts": None,
}

qu_pulse_amp_sweep = np.linspace(
    param_dict["qu_pulse_amp_start"],
    param_dict["qu_pulse_amp_stop"],
    param_dict["qu_pulse_amp_npts"],
)

if param_dict["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(qu_pulse_amp=dict(unit=""), data=dict(axes=["qu_pulse_amp"]))
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["sweep"]] = "sweeping"
    sweep_list = np.linspace(
        param_dict["sweep_start"], param_dict["sweep_stop"], param_dict["sweep_npts"]
    )
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        qu_pulse_amp=dict(unit=""),
        sweep_param=dict(unit=""),
        data=dict(axes=["qu_pulse_amp", "sweep_param"]),
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

    for sweep_param in tqdm(sweep_list):
        # update param_dict
        if not param_dict["sweep"] == False:
            param_dict[param_dict["sweep"]] = sweep_param
        exp = main_exp(session, param_dict, writer)
        compiled_exp = session.compile(exp)

        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/time_rabi_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        if param_dict["sweep"] == False:
            writer.add_data(
                qu_pulse_amp=qu_pulse_amp_sweep,
                data=data,
            )
            # plot and save the data and fitting
            inspect_decaying_oscillations_amprabi(qu_pulse_amp_sweep, data, figure=None)
            plt.savefig(f"{writer.filepath.parent}/amp_rabi.png", bbox_inches="tight")
        else:
            writer.add_data(
                qu_pulse_amp=qu_pulse_amp_sweep,
                sweep_param=sweep_param,
                data=data,
            )
