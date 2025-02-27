"""
for Transmon measurement.
CW onetone with VNA. Without Yokogawa control.
@Taketo
"""

import datetime
import json
import os
import sys
import time
from distutils.dir_util import copy_tree

import h5py
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from helpers.customized_drivers.Rohde_Schwarz_ZNA26 import RohdeSchwarzZNA26
from helpers.customized_drivers.ZNB_taketo import RohdeSchwarzZNBChannel
from helpers.setup.CW_Setup import (  # yoko_IP,
    db_path,
    db_path_local,
    param_dict,
    pd_file,
    setup_file,
    sgs_IP,
    vna_IP,
    wiring,
)
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from helpers.utilities import current_range_check
from tqdm import tqdm

sys.path.append("../analysis_code")
from CW_onetone_plot import *
from spectroscopy_1D_plot import spectroscopy_1D_plot
from spectroscopy_2D_plot import spectroscopy_2D_plot

exp_name = "CW_onetone"
tags = ["0_CW onetone"]

# define readout frequency list
freq_start = param_dict["CW_onetone"]["ro_freq_start"]
freq_stop = param_dict["CW_onetone"]["ro_freq_stop"]
if param_dict["CW_onetone"]["ro_freq_npts"] == False:
    freq_npts = (
        int((freq_stop - freq_start) / param_dict["CW_onetone"]["ro_freq_step"]) + 1
    )
else:
    freq_npts = param_dict["CW_onetone"]["ro_freq_npts"]
param_dict["CW_onetone"]["ro_freq_npts"] = freq_npts  # update freq_npts to param_dict
freq_list = np.linspace(freq_start, freq_stop, freq_npts)

# define datadict
if param_dict["CW_onetone"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="Hz"),
        # timestamp=dict(),
        # mag_dB=dict(axes=["ro_freq","timestamp"],
        #             unit="dB"),
        # phase=dict(axes=["ro_freq","timestamp"],
        #            unit="rad")
        mag_dB=dict(axes=["ro_freq"], unit="dB"),
        phase=dict(axes=["ro_freq"], unit="rad"),
    )
    datadict.validate()

elif param_dict["CW_onetone"]["sweep"] == "ro_power":
    exp_name = exp_name + "_vs_" + "power"
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["CW_onetone"]["sweep"]] = "sweeping"
    sweep_list = np.linspace(
        param_dict["sweep_start"], param_dict["sweep_stop"], param_dict["sweep_npts"]
    )
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="Hz"),
        ro_power=dict(unit="dBm"),
        mag_dB=dict(axes=["ro_freq", "ro_power"], unit="dB"),
        phase=dict(axes=["ro_freq", "ro_power"], unit="rad"),
    )
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["CW_onetone"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["CW_onetone"]["sweep"]] = "sweeping"
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
        mag_dB=dict(axes=["ro_freq", "sweep_param"], unit="dB"),
        phase=dict(axes=["ro_freq", "sweep_param"], unit="rad"),
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

    vna.rf_on()
    for sweep_param in tqdm.tqdm(sweep_list):
        # update param_dict
        if not param_dict["CW_onetone"]["sweep"] == False:
            param_dict[param_dict["CW_onetone"]["sweep"]] = sweep_param

        ## update parameters
        # setting of VNA
        vna.channels.S21.npts(freq_npts)
        vna.channels.S21.stop(freq_stop)
        vna.channels.S21.start(freq_start)
        vna.channels.S21.power.set(param_dict["ro_power"])
        vna.channels.S21.bandwidth(param_dict["vna_bw"])
        vna.channels.S21.avg(param_dict["vna_avg"])

        # measurement
        mag_dB, phase = vna.channels.S21.trace_db_phase.get()  # return unwrapped phase

        # save the data
        if param_dict["CW_onetone"]["sweep"] == False:
            writer.add_data(
                ro_freq=freq_list,
                # timestamp=timestamp,
                mag_dB=mag_dB,
                phase=phase,
            )

        elif param_dict["CW_onetone"]["sweep"] == "ro_power":
            writer.add_data(
                ro_freq=freq_list,
                ro_power=sweep_param,
                # timestamp=timestamp,
                mag_dB=mag_dB,
                phase=phase,
            )

        else:
            writer.add_data(
                ro_freq=freq_list,
                sweep_param=sweep_param,
                # timestamp=timestamp,
                mag_dB=mag_dB,
                phase=phase,
            )

    if param_dict["CW_onetone"]["sweep"] == False:
        # plot the fitting
        fig_fit, f0, fwhm = spectroscopy_1D_plot(freq_list, 10 ** (mag_dB / 20))
        fig_fit.suptitle(f"RO Power: {param_dict['ro_power']}dBm")
        fig_fit.savefig(
            f"{writer.filepath.parent}/00_1D_vs_ro_freq_fit.png", bbox_inches="tight"
        )
        writer.save_text(
            f"fitted_resonator_freq_at_ro_power_{param_dict['ro_power']}dBm.md",
            f"fitted_resonator_freq:{f0} Hz",
        )

    vna.rf_off()
    # vna.clear_channels()
    vna.close()


### plotting
path = str(filepath_parent)
# plot 1D vs ro frequency
if param_dict["CW_onetone"]["sweep"] == False:
    plotting_1D_vs_ro_freq(path)

# plot 1D vs ro power
if freq_npts == 1:
    if param_dict["CW_onetone"]["sweep"] == "ro_power":
        plotting_1D_vs_ro_power(path)
# plot 1D vs current
if freq_npts == 1:
    if param_dict["CW_onetone"]["sweep"] == "current":
        plotting_1D_vs_current(path)

# plot 1p5D vs ro_power
if not freq_npts == 1:
    if param_dict["CW_onetone"]["sweep"] == "ro_power":
        plotting_1p5D_vs_ro_power(path)
# plot 1p5D vs current
if not freq_npts == 1:
    if param_dict["CW_onetone"]["sweep"] == "current":
        plotting_1p5D_vs_current(path)

# plot 2D vs ro_freq vs ro_power
if not freq_npts == 1:
    if param_dict["CW_onetone"]["sweep"] == "ro_power":
        plotting_2D_vs_ro_power(path)
# plot 2D vs current
if not freq_npts == 1:
    if param_dict["CW_onetone"]["sweep"] == "current":
        plotting_2D_vs_current(path)

# copy the directory to the server
copy_tree(filepath_parent, new_path)
plt.show()
