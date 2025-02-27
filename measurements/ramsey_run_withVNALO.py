"""
20241020 created.
Ramsey measurement.
Use SHFQC and R&SSGS100A/Signal core for readout pulse (upconversion) and SHFQC for driving transmon.
No flux control.
"""

import os
import sys
from distutils.dir_util import copy_tree

import matplotlib.pyplot as plt
import numpy as np
import tqdm

# from qcodes.instrument_drivers.rohde_schwarz import RohdeSchwarzSGS100A
from helpers.customized_drivers.Rohde_Schwarz_ZNA26 import RohdeSchwarzZNA26
from helpers.customized_drivers.ZNB_taketo import RohdeSchwarzZNBChannel
from helpers.setup.TD_Setup import (
    db_path,
    db_path_local,
    main_descriptor,
    param_dict,
    pd_file,
    setup_file,
    sgs_IP,
    vna_IP,
    wiring,
)
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from helpers.utilities import external_average_loop
from laboneq.simple import *
from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A

sys.path.append("../analysis_code")
from inspection import inspect_decaying_oscillations
from ramsey_exp import exp_file, main_exp

exp_name = "ramsey"
tags = ["0_ramsey"]

# define pulse interval list
interval_sweep = np.linspace(
    param_dict["ramsey"]["interval_sweep_start"],
    param_dict["ramsey"]["interval_sweep_stop"],
    param_dict["ramsey"]["interval_sweep_npts"],
)

# update param_dict when local parameter used
local_param_list = param_dict["ramsey"].keys()
for key in local_param_list:
    if key in param_dict.keys():
        if not param_dict["ramsey"][key] == False:
            param_dict[key] = param_dict["ramsey"][key]

if param_dict["ramsey"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(interval=dict(unit="sec"), data=dict(axes=["interval"]))
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["ramsey"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["ramsey"]["sweep"]] = "sweeping"
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
        interval=dict(unit="sec"),
        sweep_param=dict(unit=""),
        data=dict(axes=["interval", "sweep_param"]),
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
    # sc = SC5521A('mw1')
    # connect to R&S SGS100A
    # sgsa = RohdeSchwarzSGS100A("SGSA100", sgs_IP)

    # setting of Signal Core
    # sc.power(-10) # for safety
    # sc.status("off")
    # sc.clock_frequency(10)
    # setting of R&S SGS100A
    # sgsa.status(False)
    # sgsa.power(-60) # for safety

    # connect to the equipment
    vna = RohdeSchwarzZNA26(
        "VNA",
        vna_IP,
        init_s_params=False,
        reset_channels=False,
    )

    # setting of VNA
    # keeping the current S21 settings (calibration and etc...)
    chan = RohdeSchwarzZNBChannel(
        vna,
        name="S21",
        channel=1,
        vna_parameter="S21",
        existing_trace_to_bind_to="Trc1",
    )
    vna.channels.append(chan)
    # vna.add_channel('S21')
    vna.cont_meas_on()
    vna.display_single_window()
    vna.channels.S21.power.set(-50)  # for safety

    # ZInstrument; create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)

    # sc.status('on')
    # sgsa.status(True)
    vna.rf_on()
    for sweep_param in tqdm.tqdm(sweep_list):
        # update param_dict
        if not param_dict["ramsey"]["sweep"] == False:
            param_dict[param_dict["ramsey"]["sweep"]] = sweep_param

        ## update parameters
        # setting of Signal Core
        # sc.power(param_dict["ro_exLO_power"])
        # sc.frequency(param_dict["ro_lo_plus_ro_exLO_freq"]-param_dict["ro_lo_freq"])
        # setting of SGS100A
        # sgsa.power(param_dict["qu_power"])
        # sgsa.frequency(param_dict["ro_exLO_freq"])

        ## update parameters
        # setting of VNA
        vna.channels.S21.npts(1)
        vna.channels.S21.stop(
            param_dict["ro_lo_plus_ro_exLO_freq"] - param_dict["ro_lo_freq"]
        )
        vna.channels.S21.start(
            param_dict["ro_lo_plus_ro_exLO_freq"] - param_dict["ro_lo_freq"]
        )
        vna.channels.S21.power.set(param_dict["ro_exLO_power"])
        vna.channels.S21.bandwidth(1)
        vna.channels.S21.avg(1)

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

        if param_dict["ramsey"]["sweep"] == False:
            writer.add_data(
                interval=interval_sweep,
                data=data,
            )
        else:
            writer.add_data(
                interval=interval_sweep,
                sweep_param=sweep_param,
                data=data,
            )

    # sc.status('off')
    # sgsa.status(False)
    # sc.close()
    # sgsa.close()
    vna.rf_off()
    # vna.clear_channels()
    vna.close()

### plotting
path = str(filepath_parent)
if param_dict["ramsey"]["sweep"] == False:
    # plot and save the data and fitting
    inspect_decaying_oscillations(interval_sweep, data, figure=None)
    plt.savefig(f"{writer.filepath.parent}/ramsey_inspect.png", bbox_inches="tight")

# copy the directory to the server
copy_tree(filepath_parent, new_path)

plt.show()
