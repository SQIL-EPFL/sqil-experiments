import matplotlib.pyplot as plt
import numpy as np
from amp_rabi_exp import main_exp, setup_file
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from tqdm import tqdm

exp_name = "amp_rabi_index"
tags = ["0_amp rabi_index"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7558600000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pulse_length": 56e-9,
    "qu_freq": 6232417192,
    "qu_lo_freq": 5.8e9,
    "qu_power_range": 10,
    "qu_pulse_amp_start": 0.0,
    "qu_pulse_amp_stop": 0.95,
    "qu_pulse_amp_npts": 21,
    "reset_delay": 60e-6,  # [sec]
    "avg": 2**15,
    "external_avg": 1,
    "save_pulsesheet": False,
    "index_num": 1,
}

qu_pulse_amp_sweep = np.linspace(
    param_dict["qu_pulse_amp_start"],
    param_dict["qu_pulse_amp_stop"],
    param_dict["qu_pulse_amp_npts"],
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    qu_pulse_amp=dict(unit=""),
    index=dict(unit="#"),
    data=dict(axes=["qu_pulse_amp", "index"]),
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

    for index in range(param_dict["index_num"]):
        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/time_rabi_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        writer.add_data(
            qu_pulse_amp=qu_pulse_amp_sweep,
            index=index,
            data=data,
        )
