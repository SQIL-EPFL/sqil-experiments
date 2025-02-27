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
from inspection import inspect_decaying_oscillations_amprabi, inspect_qubit_temperature
from qubit_temperature_amp_sweep_exp import exp_file, main_exp

exp_name = "Qubit_temperature_amp_sweep"
tags = ["0_qubit_temp_amp", "Q2"]

# define sweep list (ef pulse amp)
ef_pulse_amp_start = param_dict["qu_temp_amp_sweep"]["ef_pulse_amp_start"]
ef_pulse_amp_stop = param_dict["qu_temp_amp_sweep"]["ef_pulse_amp_stop"]
if param_dict["qu_temp_amp_sweep"]["ef_pulse_amp_npts"] == False:
    ef_pulse_amp_npts = (
        int(
            (ef_pulse_amp_stop - ef_pulse_amp_start)
            / param_dict["qu_temp_amp_sweep"]["ef_pulse_amp_step"]
        )
        + 1
    )
else:
    ef_pulse_amp_npts = param_dict["qu_temp_amp_sweep"]["ef_pulse_amp_npts"]
param_dict["qu_temp_amp_sweep"][
    "ef_pulse_amp_npts"
] = ef_pulse_amp_npts  # update ef_pulse_amp_npts to param_dict
ef_pulse_amp_sweep = np.linspace(
    ef_pulse_amp_start, ef_pulse_amp_stop, ef_pulse_amp_npts
)

# update param_dict when local parameter used
local_param_list = param_dict["qu_temp_amp_sweep"].keys()
for key in local_param_list:
    if key in param_dict.keys():
        if not param_dict["qu_temp_amp_sweep"][key] == False:
            param_dict[key] = param_dict["qu_temp_amp_sweep"][key]


# define DataDict for saving in DDH5 format
datadict = DataDict(
    ef_pulse_amp=dict(unit="sec"),
    index=dict(unit=""),
    data_with_ge=dict(axes=["ef_pulse_amp", "index"]),
    data_no_ge=dict(axes=["ef_pulse_amp", "index"]),
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

    # update parameters
    # setting of Signal Core
    sc.power(param_dict["ro_exLO_power"])
    sc.frequency(param_dict["ro_exLO_freq"])
    # setting of SGS100A
    # sgsa.power(param_dict["qu_power"])
    # sgsa.frequency(param_dict["ro_exLO_freq"])

    # ZInstrument; create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)
    exp_with_ge = main_exp(session, param_dict, with_ge_pi_pulse=True)
    exp_no_ge = main_exp(session, param_dict, with_ge_pi_pulse=False)
    compiled_exp_with_ge = session.compile(exp_with_ge)
    compiled_exp_no_ge = session.compile(exp_no_ge)

    if param_dict["save_pulsesheet"] == True:
        show_pulse_sheet(
            f"{writer.filepath.parent}/qubit_temperature_pulsesheet_with_ge",
            compiled_exp_with_ge,
            interactive=False,
        )
        show_pulse_sheet(
            f"{writer.filepath.parent}/qubit_temperature_pulsesheet_no_ge",
            compiled_exp_no_ge,
            interactive=False,
        )

    sc.status("on")
    # sgsa.status(True)
    for index in range(param_dict["qu_temp_amp_sweep"]["index_num"]):
        # run the experiment and take external averages
        data_with_ge = external_average_loop(
            session, compiled_exp_with_ge, param_dict["external_avg"]
        )
        data_no_ge = external_average_loop(
            session, compiled_exp_no_ge, param_dict["external_avg"]
        )
        writer.add_data(
            ef_pulse_amp=ef_pulse_amp_sweep,
            index=index,
            data_with_ge=data_with_ge,
            data_no_ge=data_no_ge,
        )

    sc.status("off")
    # sgsa.status(False)
    sc.close()
    # sgsa.close()

### plotting
path = str(filepath_parent)
# plot and save the data and fitting
if param_dict["qu_temp_amp_sweep"]["index_num"] == 1:
    inspect_qubit_temperature(
        x_array=ef_pulse_amp_sweep,
        data_with_ge=data_with_ge,
        data_no_ge=data_no_ge,
        sweep="amplitude",
        figure=None,
        real_time=False,
    )
    plt.savefig(f"{path}/qubit_temperature.png", bbox_inches="tight")
    plt.show()
    inspect_decaying_oscillations_amprabi(
        ef_pulse_amp_sweep,
        data_with_ge,
    )
    plt.savefig(f"{path}/qubit_temperature_amprabi.png", bbox_inches="tight")
    plt.show()
# copy the directory to the server
copy_tree(filepath_parent, new_path)

plt.show()
