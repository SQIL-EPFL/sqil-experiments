"""
20241018 created.
Pulsed twotone measurement.
Use SHFQC and R&SSGS100A/Signal core for readout pulse (upconversion) and SHFQC for driving transmon.
No flux control.
"""

from distutils.dir_util import copy_tree

import matplotlib.pyplot as plt
import numpy as np
import tqdm

"""
pulsed ac Stark shift measurement
"""

import os
import sys

# from helpers.customized_drivers.SignalCore_SC5511A_locking_fix import *
from helpers.customized_drivers.SignalCore_SC5511A import *
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
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from helpers.utilities import external_average_loop
from laboneq.simple import *
from qcodes.instrument_drivers.rohde_schwarz import RohdeSchwarzSGS100A
from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A

sys.path.append("../analysis_code")
from pulsed_acStarkshift_exp import exp_file, main_exp
from spectroscopy_1D_plot import spectroscopy_1D_plot
from TD_twotone_plot import *

####################################################################################
LO_source = "SignalCore"  # "SGS" or "SignalCore" # for readout
Yokogawa = False  # True or False
####################################################################################

exp_name = "pulsed_acStark_shift"
tags = ["0_pulsed_acStark_shift"]

# define readout frequency list
freq_start = param_dict["pulsed_acStark_shift"]["qu_freq_start"]
freq_stop = param_dict["pulsed_acStark_shift"]["qu_freq_stop"]
if param_dict["pulsed_acStark_shift"]["qu_freq_npts"] == False:
    freq_npts = (
        np.abs(
            int(
                (freq_stop - freq_start)
                / param_dict["pulsed_acStark_shift"]["qu_freq_step"]
            )
        )
        + 1
    )
else:
    freq_npts = param_dict["pulsed_acStark_shift"]["qu_freq_npts"]
param_dict["pulsed_acStark_shift"][
    "qu_freq_npts"
] = freq_npts  # update freq_npts to param_dict
freq_list = np.linspace(freq_start, freq_stop, freq_npts)

# update param_dict when local parameter used
local_param_list = param_dict["pulsed_acStark_shift"].keys()
for key in local_param_list:
    if key in param_dict.keys():
        if not param_dict["pulsed_acStark_shift"][key] == False:
            param_dict[key] = param_dict["pulsed_acStark_shift"][key]

# define datadict
if param_dict["pulsed_acStark_shift"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        qu_freq=dict(unit="Hz"),
        data=dict(axes=["qu_freq"]),
    )
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["pulsed_acStark_shift"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["pulsed_acStark_shift"]["sweep"]] = "sweeping"
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
        qu_freq=dict(unit="Hz"),
        sweep_param=dict(unit=""),
        data=dict(axes=["qu_freq", "sweep_param"]),
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
    sc.power(-10)  # for safety
    sc.status("off")
    sc.clock_frequency(10)

    # connect to Signal core20 GHz (cavity drive LO source)
    # sc20 = SignalCore_SC5511A("SC",'10003C68') #20GHz signal core
    # sc20.do_set_output_status(0)
    # sc20.power(-40) # for safety
    # sc20.do_set_ref_out_freq(10)
    # sc20.do_set_standby(True) # update PLL locking
    # sc20.do_set_standby(False)
    # sc20.do_set_output_status(1)

    sc20 = SignalCore_SC5511A("SC", "10003C68")
    sc20.do_set_power(-40)  # for safety
    sc20.do_set_output_status(0)
    sc20.do_set_reference_source(0)
    sc20.do_set_output_status(1)

    # ZInstrument; create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)

    sc.status("on")
    # sgsa.status(True)
    for sweep_param in tqdm.tqdm(sweep_list):
        # update param_dict
        if not param_dict["pulsed_acStark_shift"]["sweep"] == False:
            param_dict[param_dict["pulsed_acStark_shift"]["sweep"]] = sweep_param

        ## update parameters
        # setting of Signal Core
        sc.power(param_dict["ro_exLO_power"])
        sc.frequency(param_dict["ro_exLO_freq"])
        # setting of Signal Core 20GHz
        # sc20.power(param_dict["cav_drive_exLO_power"])
        # sc20.frequency(param_dict["cav_drive_exLO_freq"])
        sc20.do_set_power(param_dict["cav_drive_exLO_power"])
        sc20.do_set_frequency(param_dict["cav_drive_exLO_freq"])

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
        # save the data
        if param_dict["pulsed_acStark_shift"]["sweep"] == False:
            writer.add_data(
                qu_freq=freq_list,
                data=data,
            )
        else:
            writer.add_data(
                qu_freq=freq_list,
                sweep_param=sweep_param,
                data=data,
            )
    if param_dict["pulsed_acStark_shift"]["sweep"] == False:
        # plot the fitting
        fig_fit, f0, fwhm = spectroscopy_1D_plot(freq_list, np.abs(data))
        fig_fit.suptitle(f"RO Power: {param_dict['ro_power']}dBm")
        fig_fit.savefig(
            f"{writer.filepath.parent}/00_1D_vs_qu_freq_fit.png", bbox_inches="tight"
        )
        writer.save_text(
            f"fitted_resonator_freq_at_ro_power_{param_dict['ro_power']}dBm.md",
            f"fitted_resonator_freq:{f0} Hz",
        )

    sc.status("off")
    # sgsa.status(False)
    sc.close()
    # sgsa.close()
    sc20.do_set_output_status(0)
    sc20.close()

### plotting
path = str(filepath_parent)
# plot 1D vs ro frequency
if param_dict["pulsed_acStark_shift"]["sweep"] == False:
    plotting_1D_vs_qu_freq(path)

# copy the directory to the server
copy_tree(filepath_parent, new_path)

plt.show()
