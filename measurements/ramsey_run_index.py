import matplotlib.pyplot as plt
import numpy as np
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop, logsweep
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from ramsey_exp import main_exp, setup_file
from tqdm import tqdm

exp_name = "0_Ramsey_index"
tags = ["0_Ramsey_index", "T2_star", "TD"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7558600000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power_start": -30,
    "ro_power_stop": 1,
    "ro_power_npts": 1,
    "ro_acquire_range": -5,
    "qu_pi_pulse_length": 56e-9,
    "qu_freq": 6232417192,
    "qu_freq_detune": 0.1e6,
    "qu_lo_freq": 5.8e9,
    "qu_drive_power": 9.312,
    "interval_sweep_start": 1e-10,
    "interval_sweep_stop": 35e-6,
    "interval_sweep_npts": 35,
    "readout_delay": 0e-9,  # time interval between pulse sequence and the readout
    "reset_delay": 60e-6,  # [sec]
    "avg": 2**15,  # 2**17,
    "external_avg": 1,  # 4
    "save_pulsesheet": False,
    "index_num": 60,
}

interval_sweep = np.linspace(
    param_dict["interval_sweep_start"],
    param_dict["interval_sweep_stop"],
    param_dict["interval_sweep_npts"],
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    interval=dict(unit="sec"),
    index=dict(unit="#"),
    data=dict(axes=["interval", "index"]),
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
    exp = main_exp(session, param_dict, writer, param_dict["ro_power_start"])
    compiled_exp = session.compile(exp)
    # ro_power sweep
    for index in tqdm(range(param_dict["index_num"])):

        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/ramsey_index_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        writer.add_data(interval=interval_sweep, index=index, data=data)
