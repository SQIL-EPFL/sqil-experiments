import matplotlib.pyplot as plt
import numpy as np
from ef_time_rabi_pwm_exp import main_exp, setup_file
from helpers.inspection import inspect_decaying_oscillations
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import analyze_qspec, external_average_loop
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

exp_name = "ef_Time_Rabi_pwm"
tags = ["0_ef_timerabi_pwm"]

param_dict = {
    "ro_pulse_length": 3e-6,  # [sec]
    "ro_freq": 7558000000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pi_pulse_length": 46e-9,
    "qu_freq": 6252700000,
    "qu_lo_freq": 6.0e9,
    "qu_drive_power": 9.55,  # dBm < 26.99dBm
    "ef_pulse_length_start": 1e-10,
    "ef_pulse_length_stop": 200e-9,
    "ef_pulse_length_npts": 41,
    "ef_freq": 5878784752,
    # "ef_lo_freq":5.6e9, # cannot use different lo freq for the same output line!
    "ef_drive_power": 9.55,
    "reset_delay": 50e-6,  # [sec]
    "avg": 2**15,  # 17,
    "external_avg": 1,  # 4
    "save_pulsesheet": True,
}

ef_pulse_length_list = np.linspace(
    param_dict["ef_pulse_length_start"],
    param_dict["ef_pulse_length_stop"],
    param_dict["ef_pulse_length_npts"],
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    ef_pulse_length=dict(unit="sec"), data=dict(axes=["ef_pulse_length"])
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

    if param_dict["save_pulsesheet"] == True:
        show_pulse_sheet(
            f"{writer.filepath.parent}/ef_time_rabi_pulsesheet",
            compiled_exp,
            interactive=False,
        )

    # run the experiment and take external averages
    data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

    writer.add_data(ef_pulse_length=ef_pulse_length_list, data=data)
    # plot and save the data and fitting
    inspect_decaying_oscillations(ef_pulse_length_list, data, figure=None)
    plt.savefig(f"{writer.filepath.parent}/ef_time_rabi_pwm.png", bbox_inches="tight")
