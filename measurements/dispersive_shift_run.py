"""
Equipment:
    ZI SHFQC for readout
    ZI SHFQC for qubit drive
"""

import os
import sys
from distutils.dir_util import copy_tree

import h5py
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from dispersive_shift_exp import exp_file, main_exp
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
from helpers.utilities import external_average_loop_dispersive_ge
from laboneq.simple import *
from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A

sys.path.append("../analysis_code")
from spectroscopy_1D_plot import spectroscopy_1D_plot_dispersive_shift

exp_name = "dispersive_shift"
tags = ["0_dispersive_shift"]

# define readout frequency list
freq_start = param_dict["dispersive_shift"]["ro_freq_start"]
freq_stop = param_dict["dispersive_shift"]["ro_freq_stop"]
if param_dict["dispersive_shift"]["ro_freq_npts"] == False:
    freq_npts = (
        int((freq_stop - freq_start) / param_dict["dispersive_shift"]["ro_freq_step"])
        + 1
    )
else:
    freq_npts = param_dict["dispersive_shift"]["ro_freq_npts"]
param_dict["dispersive_shift"][
    "ro_freq_npts"
] = freq_npts  # update freq_npts to param_dict
freq_list = np.linspace(freq_start, freq_stop, freq_npts)

# update param_dict when local parameter used
local_param_list = param_dict["dispersive_shift"].keys()
for key in local_param_list:
    if key in param_dict.keys():
        if not param_dict["dispersive_shift"][key] == False:
            param_dict[key] = param_dict["dispersive_shift"][key]

# define datadict
if param_dict["dispersive_shift"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="Hz"),
        ground_data=dict(axes=["ro_freq"]),
        excited_data=dict(axes=["ro_freq"]),
    )
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["dispersive_shift"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["dispersive_shift"]["sweep"]] = "sweeping"
    if param_dict["sweep_list"] == False:
        sweep_list = np.linspace(
            param_dict["sweep_start"],
            param_dict["sweep_stop"],
            param_dict["sweep_npts"],
        )
        param_dict["sweep_list"] = sweep_list
    else:
        sweep_list = param_dict["sweep_list"]
        param_dict["sweep_start"] = False
        param_dict["sweep_stop"] = False
        param_dict["sweep_npts"] = False
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="Hz"),
        sweep_param=dict(unit=""),
        ground_data=dict(axes=["ro_freq", "sweep_param"]),
        excited_data=dict(axes=["ro_freq", "sweep_param"]),
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

    sc.status("on")
    # sgsa.status(True)
    for sweep_param in tqdm.tqdm(sweep_list):
        # update param_dict
        if not param_dict["dispersive_shift"]["sweep"] == False:
            param_dict[param_dict["dispersive_shift"]["sweep"]] = sweep_param

        ## update parameters
        # setting of Signal Core
        sc.power(param_dict["ro_exLO_power"])
        sc.frequency(param_dict["ro_exLO_freq"])
        # setting of SGS100A
        # sgsa.power(param_dict["qu_power"])
        # sgsa.frequency(param_dict["ro_exLO_freq"])

        # define ZI experiment
        exp = main_exp(session, param_dict)
        compiled_exp = session.compile(exp)

        # output and save a pulse sheet
        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/pulsesheet", compiled_exp, interactive=False
            )

        # run the experiment and take external averages
        data0, data1 = external_average_loop_dispersive_ge(
            session,
            compiled_exp,
            param_dict["external_avg"],
        )
        # save the data
        if param_dict["pulsed_onetone"]["sweep"] == False:
            writer.add_data(ro_freq=freq_list, ground_data=data0, excited_data=data1)
        else:
            writer.add_data(
                ro_freq=freq_list,
                sweep_param=sweep_param,
                ground_data=data0,
                excited_data=data1,
            )

if param_dict["dispersive_shift"]["sweep"] == False:
    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    ro_freq = h5file["data"]["ro_freq"][:]
    ground_data = h5file["data"]["ground_data"][:]
    excited_data = h5file["data"]["excited_data"][:]
    fig_1D_plot, res_freq_multi, FWHM_multi = spectroscopy_1D_plot_dispersive_shift(
        ro_freq,
        [ground_data, excited_data],
        ["g-state", "e-state"],
        "RO Frequency [Hz]",
        "Mag []",
        ["blue", "red"],
    )

    fig_1D_plot.suptitle("Dispersive Shift")
    fig_1D_plot.savefig(f"{filepath_parent}/1D_plot.png", bbox_inches="tight")

    with open(str(filepath_parent) + "/fitted_parameters.md", "w+") as f:
        f.write("freq g-state[Hz]: " + str(int(res_freq_multi[0])) + "\n")
        f.write("freq e-state[Hz]: " + str(int(res_freq_multi[1])) + "\n")
        chi = res_freq_multi[1] - res_freq_multi[0]
        f.write("chi[Hz]: " + str(int(chi)) + "\n")

# copy the directory to the server
copy_tree(filepath_parent, new_path)
