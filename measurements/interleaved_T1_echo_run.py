"""
20241020 created.
interleaved T1 T2 measurement.
Use SHFQC and R&SSGS100A/Signal core for readout pulse (upconversion) and SHFQC for driving transmon.
No flux control.
"""

import os
import sys
from distutils.dir_util import copy_tree

import h5py
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from helpers.setup.TD_Setup import (
    db_path,
    db_path_local,
    main_descriptor,
    param_dict,
    pd_file,
    setup_file,
    sgs_IP,
    wiring,
)

# from qcodes.instrument_drivers.rohde_schwarz import RohdeSchwarzSGS100A
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from helpers.utilities import external_average_loop_2data
from laboneq.simple import *
from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A

sys.path.append("../analysis_code")
from inspection import inspect_decaying_exponent
from interleaved_T1_echo_exp import exp_file, main_exp
from interleaved_T1_echo_plot import interleaved_T1_echo_plot

exp_name = "interleaved"
tags = ["0_interleaved"]

T1_delay_list = param_dict["interleaved"]["delay_sweep_list"]

echo_interval_list = param_dict["interleaved"]["interval_sweep_list"]

# update param_dict when local parameter used
local_param_list = param_dict["interleaved"].keys()
for key in local_param_list:
    if key in param_dict.keys():
        if not param_dict["interleaved"][key] == False:
            param_dict[key] = param_dict["interleaved"][key]

# define DataDict for saving in DDH5 format
datadict = DataDict(
    T1_delay=dict(unit="sec"),
    echo_interval_delay=dict(unit="sec"),
    index=dict(unit="#"),
    data_T1=dict(axes=["T1_delay", "index"]),
    data_echo=dict(axes=["echo_interval_delay", "index"]),
)
datadict.validate()

with DDH5Writer(datadict, db_path_local, name=exp_name) as writer:
    filepath_parent = writer.filepath.parent
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, pd_file])
    writer.save_text("wiring.md", wiring)

    # take the last two stages of the filepath_parent
    path = str(filepath_parent)
    last_two_parts = path.split(os.sep)[-2:]
    new_path = os.path.join(db_path, *last_two_parts)
    writer.save_text("directry_path.md", new_path)

    ## connect to the equipment
    # connect to Signal core (LO source)
    sc = SC5521A("mw1")
    # connect to R&S SGS100A
    # sgsa = RohdeSchwarzSGS100A("SGSA100", sgs_IP)

    # setting of Signal Core
    sc.power(-10)  # for safety
    sc.status("off")
    sc.clock_frequency(10)
    # setting of R&S SGS100A
    # sgsa.status(False)
    # sgsa.power(-60) # for safety

    # ZInstrument; create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)
    exp = main_exp(session, param_dict)
    compiled_exp = session.compile(exp)

    sc.status("on")
    # sgsa.status(True)
    ## update parameters
    # setting of SGS100A
    sc.power(param_dict["ro_exLO_power"])
    sc.frequency(param_dict["ro_exLO_freq"])

    for index in range(param_dict["interleaved"]["index_num"]):
        if (
            param_dict["interleaved"]["index_num"] == 1
            and param_dict["save_pulsesheet"] == True
        ):
            show_pulse_sheet(
                f"{writer.filepath.parent}/interleaved_T1_echo_pulsesheet",
                compiled_exp,
                interactive=False,
            )

        # run the experiment and take external averages
        data_T1, data_echo = external_average_loop_2data(
            session, compiled_exp, param_dict["external_avg"]
        )

        writer.add_data(
            T1_delay=T1_delay_list,
            echo_interval_delay=echo_interval_list,
            index=index,
            data_T1=data_T1,
            data_echo=data_echo,
        )

    sc.status("off")
    # sgsa.status(False)
    sc.close()
    # sgsa.close()


# reload all data after writer-object is released, and plot statistics
filename = os.path.join(filepath_parent, "data.ddh5")
h5file = h5py.File(filename, "r")

T1_data = h5file["data"]["data_T1"][::] * 1e3  # transform to unit us
T1_delay = h5file["data"]["T1_delay"][0] * 1e6  # transform to unit s
echo_data = h5file["data"]["data_echo"][::] * 1e3  # transform to unit us
echo_interval_delay = h5file["data"]["echo_interval_delay"][0] * 1e6
index_list = h5file["data"]["index"]

fig_indexed, fig_stats, T1, T2echo, Tphi, T1_std, T2echo_std, Tphi_std = (
    interleaved_T1_echo_plot(
        index_list, T1_delay, T1_data, echo_interval_delay, echo_data, sigma_filter=True
    )
)

fig_indexed.savefig(
    f"{filepath_parent}/interleaved_measurement.png", bbox_inches="tight"
)
fig_stats.savefig(
    f"{filepath_parent}/interleaved_measurement_stats.png", bbox_inches="tight"
)

with open(str(filepath_parent) + "/fitted_parameters.md", "w") as f:
    f.write("T1: " + str(T1) + "us +- " + str(T1_std) + "us \n")
    f.write("T2 echo: " + str(T2echo) + "us +- " + str(T2echo_std) + "us \n")
    f.write("Tphi: " + str(Tphi) + "us +- " + str(Tphi_std) + "us \n")

# copy the directory to the server
copy_tree(filepath_parent, new_path)
