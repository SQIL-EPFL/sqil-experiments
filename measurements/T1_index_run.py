import matplotlib.pyplot as plt
import numpy as np
from helpers.inspection import inspect_decaying_exponent
from helpers.TD_setup_righttransmon import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop, logsweep
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from T1_exp import main_exp, setup_file

exp_name = "0_T1_index"
tags = ["0_T1_index", "TD"]

param_dict = {
    "ro_pulse_length": 3e-6,  # [sec]
    "ro_freq": 7557906800,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power_start": -20,
    "ro_power_stop": 1,
    "ro_power_npts": 1,
    "ro_acquire_range": -5,
    "qu_pi_pulse_length": 125e-9,
    "qu_freq": 6219934629,
    "qu_lo_freq": 6.0e9,
    "qu_drive_power": 9.55,
    "logsweep": True,
    "delay_sweep_list": np.hstack(
        [np.linspace(1e-10, 30e-6, 20), logsweep(31e-6, 60e-6, 11)]
    ),
    "delay_sweep_start": 1e-10,
    "delay_sweep_stop": 100e-6,
    "delay_sweep_npts": 31,
    "reset_delay": 50e-6,  # [sec]
    "avg": 2**14,  # 17,
    "external_avg": 1,  # 4
    "save_pulsesheet": True,
    "index_num": 1000,
}

delay_sweep = param_dict["delay_sweep_list"]

# define DataDict for saving in DDH5 format
datadict = DataDict(
    readout_delay=dict(unit="sec"),
    index=dict(unit="#"),
    data=dict(axes=["readout_delay", "index"]),
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

    for index in range(param_dict["index_num"]):
        # if param_dict["save_pulsesheet"]==True:
        #     show_pulse_sheet(f"{writer.filepath.parent}/ro_power_{ro_power}dBm_pulsesheet",
        #                      compiled_exp,
        #                      interactive=False)

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        writer.add_data(readout_delay=delay_sweep, index=index, data=data)

        # # plot and save the data and fitting
        # inspect_decaying_exponent(delay_sweep, data, figure=None)
        # plt.savefig(f"{writer.filepath.parent}/ro_power_{ro_power}dBm.png", bbox_inches='tight')
