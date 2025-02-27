"""
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
from helpers.utilities import compute_threshold
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from single_shot_RAW_trace_exp import main_exp, setup_file

sys.path.append("../analysis_code")
from raw_trace import raw_trace_plot


def trace_rand(length, offset):
    return np.random.normal(offset, 1, length)


exp_name = "single_shot_RAW_trace"
tags = ["0_single_shot_RAW_trace"]

param_dict = {
    "ro_pulse_length": 1024
    * 0.5e-9,  # 0.5e-9, #[sec], assuming that the sampling rate is 0.5e-9, and the RAW trace contains 4096 datapoints * FIXED!! *
    "ro_freq": 7563621326,
    "ro_lo_freq": 7.1e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pi_pulse_length": 64e-9,
    "qu_freq": 6186646414,
    "qu_lo_freq": 5.7e9,
    "qu_drive_power": 9.18,
    "reset_delay": 60e-6,  # [sec]
    "repeats": 1,
    "save_pulsesheet": True,
    "plot_distribution": True,
    "do_emulate": False,
}


# define DataDict for saving in DDH5 format
datadict = DataDict(
    repetition_id=dict(unit=""),
    raw_datapoint_id=dict(unit=""),
    ground_data=dict(
        axes=[
            "repetition_id",
            "raw_datapoint_id",
        ],
        unit="",
    ),
    excited_data=dict(
        axes=[
            "repetition_id",
            "raw_datapoint_id",
        ],
        unit="",
    ),
)
datadict.validate()

with DDH5Writer(datadict, db_path, name=exp_name) as writer:
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, descriptor_file])
    writer.save_text("directry_path.md", f"{writer.filepath.parent}")

    for iteration in range(0, param_dict["repeats"]):
        # create and connect to a session
        device_setup = DeviceSetup.from_descriptor(main_descriptor)
        session = Session(device_setup=device_setup)
        session.connect(do_emulation=param_dict["do_emulate"], reset_devices=True)

        exp = main_exp(session, param_dict, writer)
        compiled_exp = session.compile(exp)

        # output and save a pulse sheet
        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/pulsesheet", compiled_exp, interactive=False
            )

        laboneq_result = session.run(compiled_exp)
        data0 = laboneq_result.get_data("ground_state")
        data1 = laboneq_result.get_data("excited_state")

        # overwrite with fake data:
        if param_dict["do_emulate"]:
            data0 = trace_rand(4096, 1)
            data1 = trace_rand(4096, 0.8)

        # save the data in DDH5 file
        writer.add_data(
            repetition_id=iteration,
            raw_datapoint_id=np.indices(data0.shape),  # might not work
            ground_data=data0,
            excited_data=data1,
        )

        filepath_parent = writer.filepath.parent


if param_dict["plot_distribution"] == True:

    plt.close("all")

    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    db_repeats = h5file["data"]["repetition_id"][:]

    db_ground_data = h5file["data"]["ground_data"][:][:]
    db_excited_data = h5file["data"]["excited_data"][:][:]

    fig_raw_trace = raw_trace_plot(db_repeats, [db_ground_data, db_excited_data])
    fig_raw_trace.savefig(f"{filename}/raw_trace_averaged.png", bbox_inches="tight")
