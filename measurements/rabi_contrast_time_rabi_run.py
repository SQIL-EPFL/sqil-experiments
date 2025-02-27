import matplotlib.pyplot as plt
import numpy as np
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

# from helpers.inspection import inspect_decaying_oscillations
from rabi_contrast_time_rabi_exp import main_exp, setup_file
from tqdm import tqdm

exp_name = "rabi_contrast_time_rabi"
tags = ["0_rabi_contrast_time_rabi", "TD"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7558600000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pulse_length_start": 10e-9,
    "qu_pulse_length_stop": 130e-9,
    "qu_pulse_length_npts": 21,
    "qu_freq": 6232417192,
    "qu_lo_freq": 5.8e9,
    "qu_drive_power": 9.55,
    "reset_delay": 60e-6,  # [sec]
    "avg": 2**15,
    "external_avg": 1,
    "save_pulsesheet": False,
    "sweep": "ro_pulse_length",  # str. name of the parameter in param_dict: "ro_freq", "ro_power", "ro_pulse_length"
    "sweep_start": 1e-6,  # 7553600000, #-40 , #1e-6
    "sweep_stop": 10e-6,  # 7563600000, #-20 , #3e-6
    "sweep_npts": 181,
}

qu_pulse_length_sweep = np.linspace(
    param_dict["qu_pulse_length_start"],
    param_dict["qu_pulse_length_stop"],
    param_dict["qu_pulse_length_npts"],
)

if param_dict["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        qu_pulse_length=dict(unit="sec"), data=dict(axes=["qu_pulse_length"])
    )
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
        qu_pulse_length=dict(unit="sec"),
        sweep_param=dict(unit=""),
        data=dict(axes=["qu_pulse_length", "sweep_param"]),
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
                qu_pulse_length=qu_pulse_length_sweep,
                data=data,
            )
            # plot and save the data and fitting
            # inspect_decaying_oscillations(qu_pulse_length_sweep, data, figure=None)
            # plt.savefig(f"{writer.filepath.parent}/time_rabi.png", bbox_inches='tight')
        else:
            writer.add_data(
                qu_pulse_length=qu_pulse_length_sweep,
                sweep_param=sweep_param,
                data=data,
            )
