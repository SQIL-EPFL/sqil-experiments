import matplotlib.pyplot as plt
import numpy as np
from echo_cpmg_SGS_exp import main_exp, setup_file
from helpers.inspection import inspect_decaying_exponent
from helpers.TD_setup_left_line_SGS import sgsa  # Rohde_Schwarz SGS100A
from helpers.TD_setup_left_line_SGS import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop, logsweep
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

exp_name = "Echo_CPMG_vs_ro_power"
tags = ["0_Echo", "0_CPMG", "T2", "TD", "SGS"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq": 7558000000,
    "ro_lo_freq": 7.3e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -20,
    "ro_acquire_range": -5,
    "qu_pi_pulse_length": 516e-9,
    "qu_freq": 6252791992,
    "qu_power_range": 0.4,  # 400mV. Should not exceed 0.5 in total voltage!!!
    "qu_pulse_amp": 0.95,  # better not exceed 0.95 (causing overload on HDAWG)
    "sgsa_power": -10,
    "pi_pulse_rep": 1,  # 1 corresponds to echo, (2*N - 1) pi pulse
    "logsweep": True,
    "interval_sweep_list": np.hstack(
        [np.linspace(0, 50e-6, 21), logsweep(52.5e-6, 100e-6, 11)]
    ),
    "interval_sweep_start": 1e-10,
    "interval_sweep_stop": 100e-6,
    "interval_sweep_npts": 32,
    "readout_delay": 0e-9,  # time interval between pulse sequence and the readout
    "reset_delay": 150e-6,  # [sec]
    "avg": 2**15,  # 2**17,
    "external_avg": 1,  # 4
    "save_pulsesheet": True,
}
if param_dict["logsweep"] == True:
    interval_sweep = param_dict["interval_sweep_list"]
else:
    interval_sweep = np.linspace(
        param_dict["interval_sweep_start"],
        param_dict["interval_sweep_stop"],
        param_dict["interval_sweep_npts"],
    )

# define DataDict for saving in DDH5 format
datadict = DataDict(interval=dict(unit="sec"), data=dict(axes=["interval"]))
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

    exp = main_exp(session, param_dict, writer)
    compiled_exp = session.compile(exp)

    if param_dict["save_pulsesheet"] == True:
        show_pulse_sheet(
            f"{writer.filepath.parent}/echo_cpmg_pulsesheet",
            compiled_exp,
            interactive=False,
        )

    # run the experiment and take external averages
    data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

    writer.add_data(interval=interval_sweep, data=data)
    # plot and save the data and fitting
    inspect_decaying_exponent(interval_sweep, data, figure=None)
    plt.savefig(f"{writer.filepath.parent}/echo_cpmg.png", bbox_inches="tight")
sgsa.off()
sgsa.close()
