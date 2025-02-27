import matplotlib.pyplot as plt
import numpy as np
from helpers.inspection import inspect_decaying_exponent
from helpers.TD_setup_left_line_SGS import sgsa  # Rohde_Schwarz SGS100A
from helpers.TD_setup_left_line_SGS import db_path, descriptor_file, main_descriptor
from helpers.utilities import external_average_loop_interleaved_T1_echo, logsweep
from interleaved_T1_echo_SGS_exp import main_exp, setup_file
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

exp_name = "0_interleaved_T1_echo"
tags = ["0_interleaved_T1_echo", "TD", "SGS"]

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
    # for T1 measurement
    "delay_sweep_list": np.hstack(
        [np.linspace(0, 10e-6, 21), logsweep(11e-6, 50e-6, 11)]
    ),
    # for echo measurement
    "interval_sweep_list": np.hstack(
        [np.linspace(0, 50e-6, 21), logsweep(52.5e-6, 90e-6, 11)]
    ),
    "readout_delay": 0e-6,
    "reset_delay": 150e-6,  # [sec]
    "avg": 2**15,  # 17,
    "external_avg": 1,  # 4
    "save_pulsesheet": True,
    "index_num": 2000,
}

T1_delay_list = param_dict["delay_sweep_list"]

echo_interval_list = param_dict["interval_sweep_list"]

# define DataDict for saving in DDH5 format
datadict = DataDict(
    T1_delay=dict(unit="sec"),
    echo_interval_delay=dict(unit="sec"),
    index=dict(unit="#"),
    data_T1=dict(axes=["T1_delay", "index"]),
    data_echo=dict(axes=["echo_interval_delay", "index"]),
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

    sgsa.power(param_dict["sgsa_power"])
    sgsa.frequency(param_dict["qu_freq"])
    sgsa.on()
    # ro_power sweep
    for index in range(param_dict["index_num"]):
        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/interleaved_T1_echo_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data_T1, data_echo = external_average_loop_interleaved_T1_echo(
            session, compiled_exp, param_dict["external_avg"]
        )

        writer.add_data(
            T1_delay=T1_delay_list,
            echo_interval_delay=echo_interval_list,
            index=index,
            data_T1=data_T1,
            data_echo=data_echo,
        )
sgsa.off()
sgsa.close()
