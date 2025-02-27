"""
20241020 created.
pulse_train measurement.
Use SHFQC and R&SSGS100A/Signal core for readout pulse (upconversion) and SHFQC for driving transmon.
No flux control.
"""

import os
import sys
from distutils.dir_util import copy_tree

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
from helpers.utilities import external_average_loop
from laboneq.simple import *
from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A

sys.path.append("../analysis_code")
from pulse_train_exp import exp_file, main_exp

exp_name = "pulse_train"
tags = ["0_pulse_train"]

reps_sweep = np.linspace(
    param_dict["pulse_train"]["reps_sweep_start"],
    param_dict["pulse_train"]["reps_sweep_stop"],
    param_dict["pulse_train"]["reps_sweep_npts"],
)

# update param_dict when local parameter used
local_param_list = param_dict["pulse_train"].keys()
for key in local_param_list:
    if key in param_dict.keys():
        if not param_dict["pulse_train"][key] == False:
            param_dict[key] = param_dict["pulse_train"][key]

if param_dict["pulse_train"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(reps=dict(unit="#"), data=dict(axes=["reps"]))
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["pulse_train"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["pulse_train"]["sweep"]] = "sweeping"
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
        reps=dict(unit="#"),
        sweep_param=dict(unit=""),
        data=dict(axes=["reps", "sweep_param"]),
    )
    datadict.validate()

with DDH5Writer(datadict, db_path_local, name=exp_name) as writer:
    filepath_parent = writer.filepath.parent
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, pd_file, exp_file])
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
        if not param_dict["pulse_train"]["sweep"] == False:
            param_dict[param_dict["pulse_train"]["sweep"]] = sweep_param

        ## update parameters
        # setting of SGS100A
        sc.power(param_dict["ro_exLO_power"])
        sc.frequency(param_dict["ro_exLO_freq"])

        # define ZI experiment
        exp = main_exp(session, param_dict)
        compiled_exp = session.compile(exp)

        # output and save a pulse sheet
        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/pulsesheet", compiled_exp, interactive=False
            )

        # run the experiment and take external averages
        data = external_average_loop(session, compiled_exp, param_dict["external_avg"])

        if param_dict["pulse_train"]["sweep"] == False:
            writer.add_data(
                reps=reps_sweep,
                data=data,
            )
        else:
            writer.add_data(
                reps=reps_sweep,
                sweep_param=sweep_param,
                data=data,
            )

    sc.status("off")
    # sgsa.status(False)
    sc.close()
    # sgsa.close()

### plotting
path = str(filepath_parent)

# copy the directory to the server
copy_tree(filepath_parent, new_path)

plt.show()
