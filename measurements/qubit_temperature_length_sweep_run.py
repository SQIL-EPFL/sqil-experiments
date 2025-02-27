import sys

import matplotlib.pyplot as plt
import numpy as np
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import analyze_qspec, external_average_loop
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

sys.path.append("../analysis_code")
from inspection import inspect_qubit_temperature
from qubit_temperature_length_sweep_exp import main_exp, setup_file

exp_name = "Qubit_temperature_length_sweep"
tags = ["0_qubit_temp_length", "TD"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7566991270,  # use e-frequency, instead of cavity frequency!!!
    "ro_lo_freq": 7.1e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    # qubit1
    "qu_pi_pulse_length": 64e-9,
    "qu_freq": 6238372448,
    "qu_lo_freq": 5.8e9,
    "qu_drive_power": 9.33,
    "ef_freq": 5863829442,
    "ef_drive_power": 9.55,  # neglected when "sweep"=="amplitude"
    "ef_pulse_length_start": 1e-10,
    "ef_pulse_length_stop": 200e-9,
    "ef_pulse_length_npts": 21,
    "reset_delay": 60e-6,  # [sec]
    "avg": 2**15,
    "external_avg": 1,
    "index_num": 1,
    "save_pulsesheet": False,
    "plot_inspection": True,
}
ef_pulse_length_list = np.linspace(
    param_dict["ef_pulse_length_start"],
    param_dict["ef_pulse_length_stop"],
    param_dict["ef_pulse_length_npts"],
)
# define DataDict for saving in DDH5 format
datadict = DataDict(
    ef_pulse_length=dict(unit="sec"),
    index=dict(unit="#"),
    data_with_ge=dict(axes=["ef_pulse_length", "index"]),
    data_no_ge=dict(axes=["ef_pulse_length", "index"]),
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
    exp_with_ge = main_exp(session, param_dict, writer, with_ge_pi_pulse=True)
    exp_no_ge = main_exp(session, param_dict, writer, with_ge_pi_pulse=False)
    compiled_exp_with_ge = session.compile(exp_with_ge)
    compiled_exp_no_ge = session.compile(exp_no_ge)

    if param_dict["save_pulsesheet"] == True:
        show_pulse_sheet(
            f"{writer.filepath.parent}/qubit_temperature_pulsesheet_with_ge",
            compiled_exp_with_ge,
            interactive=False,
        )
        show_pulse_sheet(
            f"{writer.filepath.parent}/qubit_temperature_pulsesheet_no_ge",
            compiled_exp_no_ge,
            interactive=False,
        )

    for index in range(param_dict["index_num"]):
        # run the experiment and take external averages
        data_with_ge = external_average_loop(
            session, compiled_exp_with_ge, param_dict["external_avg"]
        )
        data_no_ge = external_average_loop(
            session, compiled_exp_no_ge, param_dict["external_avg"]
        )
        writer.add_data(
            ef_pulse_length=ef_pulse_length_list,
            index=index,
            data_with_ge=data_with_ge,
            data_no_ge=data_no_ge,
        )
        if param_dict["plot_inspection"] == True:
            # plot and save the data and fitting
            inspect_qubit_temperature(
                x_array=ef_pulse_length_list,
                data_with_ge=data_with_ge,
                data_no_ge=data_no_ge,
                sweep="length",
                figure=None,
                real_time=False,
            )
            plt.savefig(
                f"{writer.filepath.parent}/qubit_temperature.png", bbox_inches="tight"
            )
