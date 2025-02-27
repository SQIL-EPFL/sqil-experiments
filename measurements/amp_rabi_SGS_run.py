import matplotlib.pyplot as plt
import numpy as np
from helpers.inspection import inspect_decaying_oscillations
from helpers.TD_setup_left_line_SGS import sgsa  # Rohde_Schwarz SGS100A
from helpers.TD_setup_left_line_SGS import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from time_rabi_SGS_exp import main_exp, setup_file

exp_name = "amp_rabi"
tags = ["0_amp rabi", "TD", "SGS"]

param_dict = {
    "ro_pulse_length": 3e-6,  # [sec]
    "ro_freq": 7558000000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power_start": -30,
    "ro_power_stop": 1,
    "ro_power_npts": 1,
    "ro_acquire_range": -5,
    "qu_pulse_length": 100e-9,
    "qu_freq": 6252700000,
    "qu_pulse_amp_start": 0,
    "qu_pulse_amp_stop": 0.95,  # better not exceed 0.95 (causing overload on HDAWG)
    "qu_pulse_amp_npts": 1,
    "qu_power_range": 0.4,  # 400mV. Should not exceed 0.5 in total voltage!!!
    "sgsa_power": 0,
    "reset_delay": 60e-6,  # [sec]
    "avg": 2**14,
    "external_avg": 1,
    "save_pulsesheet": True,
}

qu_pulse_amp_sweep = np.linspace(
    param_dict["qu_pulse_amp_start"],
    param_dict["qu_pulse_amp_stop"],
    param_dict["qu_pulse_amp_npts"],
)
ro_power_sweep = np.linspace(
    param_dict["ro_power_start"],
    param_dict["ro_power_stop"],
    param_dict["ro_power_npts"],
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    qu_pulse_amp=dict(unit=""),
    ro_power=dict(unit="dBm"),
    data=dict(axes=["qu_pulse_length", "ro_power"]),
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

    sgsa.power(param_dict["sgsa_power"])
    sgsa.frequency(param_dict["qu_freq"])
    sgsa.on()
    # ro_power sweep
    for ro_power in ro_power_sweep:
        exp = main_exp(session, param_dict, writer)
        compiled_exp = session.compile(exp)

        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/ro_power_{ro_power}dBm_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        writer.add_data(
            qu_pulse_amp=qu_pulse_amp_sweep,
            ro_power=ro_power,
            data=data,
        )

        # plot and save the data and fitting
        inspect_decaying_oscillations(qu_pulse_amp_sweep, data, figure=None)
        plt.savefig(f"{writer.filepath.parent}/amp_rabi.png", bbox_inches="tight")
sgsa.off()
sgsa.close()
