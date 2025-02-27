"""
for fluxonium measurement.
CW twotone with VNA and Signal Core.
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

# from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A
from qcodes.instrument_drivers.rohde_schwarz import RohdeSchwarzSGS100A

sys.path.append("../analysis_code")
from CW_onetone_plot import (
    flatten_phase,
    mag_phase_1D_plot,
    mag_phase_1p5D_plot,
    mag_phase_2D_plot,
    offset_for_1p5D_plot,
)
from spectroscopy_1D_plot import spectroscopy_1D_plot
from spectroscopy_2D_plot import spectroscopy_2D_plot

exp_name = "CW_twotone_sweep_ro_freq"
tags = ["0_CW twotone_sweep_ro_freq", "sweep_ro_freq"]

# define qubit drive frequency list
freq_start = param_dict["CW_twotone_sweep_ro_freq"]["ro_freq_start"]
freq_stop = param_dict["CW_twotone_sweep_ro_freq"]["ro_freq_stop"]
if param_dict["CW_twotone_sweep_ro_freq"]["ro_freq_npts"] == False:
    freq_npts = (
        int(
            abs(freq_stop - freq_start)
            / param_dict["CW_twotone_sweep_ro_freq"]["ro_freq_step"]
        )
        + 1
    )
else:
    freq_npts = param_dict["CW_twotone_sweep_ro_freq"]["ro_freq_npts"]
param_dict["CW_twotone_sweep_ro_freq"][
    "ro_freq_npts"
] = freq_npts  # update freq_npts to param_dict
freq_list = np.linspace(freq_start, freq_stop, freq_npts)

# define datadict
if param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="sec"),
        mag_dB=dict(axes=["ro_freq"], unit="dB"),
        phase=dict(axes=["ro_freq"], unit="rad"),
    )
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["CW_twotone_sweep_ro_freq"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["CW_twotone_sweep_ro_freq"]["sweep"]] = "sweeping"
    if param_dict["sweep_list"] == False:
        sweep_list = np.linspace(
            param_dict["sweep_start"],
            param_dict["sweep_stop"],
            param_dict["sweep_npts"],
        )
    else:
        sweep_list = param_dict["sweep_list"]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="sec"),
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
    # sc = SC5521A('mw1')
    sgsa = RohdeSchwarzSGS100A("SGSA100", sgs_IP)

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
    # vna.cont_meas_on()
    # vna.display_single_window()
    # vna.channels.S21.sweep_type('CW_Point')
    # vna.channels.S21.power.set(-50) # for safety

    # vna.add_channel('S21')
    vna.cont_meas_on()
    vna.display_single_window()
    vna.channels.S21.power.set(-50)  # for safety

    # setting of signal core
    sgsa.status(False)
    sgsa.power(-60)  # for safety

    vna.rf_on()
    # sc.status('on')
    sgsa.status(True)
    for sweep_param in tqdm.tqdm(sweep_list):
        # update param_dict
        if not param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == False:
            param_dict[param_dict["CW_twotone_sweep_ro_freq"]["sweep"]] = sweep_param

        ## update parameters
        # setting of VNA
        vna.channels.S21.npts(freq_npts)
        vna.channels.S21.stop(freq_stop)
        vna.channels.S21.start(freq_start)
        vna.channels.S21.power.set(param_dict["ro_power"])
        vna.channels.S21.bandwidth(param_dict["vna_bw"])
        vna.channels.S21.avg(param_dict["vna_avg"])

        # setting of Signal Core
        # sc.power(param_dict["qu_power"])
        # sc.frequency(param_dict["qu_freq"])
        sgsa.power(param_dict["qu_power"])
        sgsa.frequency(param_dict["qu_freq"])

        # measurement
        mag_dB, phase = vna.channels.S21.trace_db_phase.get()  # return unwrapped phase

        # save the data
        if param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == False:
            writer.add_data(ro_freq=freq_list, mag_dB=mag_dB, phase=phase)
        else:
            writer.add_data(
                ro_freq=freq_list, sweep_param=sweep_param, mag_dB=mag_dB, phase=phase
            )

        # plot the single trace
        if param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == False:
            fig_fit, f0, fwhm = spectroscopy_1D_plot(freq_list, 10 ** (mag_dB / 20))
            fig_fit.suptitle(
                f"ro_power={param_dict["ro_power"]}dBm, "
                + f"qu_freq={param_dict["qu_freq"]*1e-9}GHz, "
                + f"qu_power={param_dict["qu_power"]}dBm \n"
                + f"current={param_dict["current"]*1e3}mA"
            )
            fig_fit.savefig(
                f"{writer.filepath.parent}/ro_power_{param_dict["ro_power"]}dBm_fit.png",
                bbox_inches="tight",
            )
            writer.save_text(
                f"fitted_resonator_freq_at_ro_power_{param_dict["ro_power"]}dBm.md",
                f"fitted_ro_freq:{f0} Hz",
            )

    vna.rf_off()
    # sc.status('off')
    sgsa.status(False)
    vna.close()
    # sc.close()
    sgsa.close()

##################################################################################
path = str(filepath_parent)

# plot 1D vs ro frequency
if param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == False:
    filename = path + r"\data.ddh5"
    h5file = h5py.File(filename, "r")
    mag1D = np.array(h5file["data"]["mag_dB"][:])
    phase1D = np.array(h5file["data"]["phase"][:])
    phase1D = flatten_phase(phase1D)
    ro_freq = np.array(h5file["data"]["ro_freq"][:]) * 1e-9  # [GHz]
    xlabel = "Readout frequency [GHz]"

    param_dict_path = path + r"\param_dict.json"
    with open(param_dict_path) as f:
        param_dict = json.load(f)

    title = (
        f"ro_power={param_dict['ro_power']}dBm, "
        + f"current={param_dict['current']*1e3}mA"
    )

    fig = mag_phase_1D_plot(mag1D, phase1D, ro_freq, xlabel, title)
    fig.tight_layout()
    fig.savefig(f"{path}/1D_vs_ro_freq.png", bbox_inches="tight")

# plot 1D vs ro power
if freq_npts == 1:
    if param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == "ro_power":
        filename = path + r"\data.ddh5"
        h5file = h5py.File(filename, "r")
        mag1D = np.array(h5file["data"]["mag_dB"][:])
        phase1D = np.array(h5file["data"]["phase"][:])
        ro_power = np.array(h5file["data"]["ro_power"][:])  # [dBm]
        xlabel = "Readout power [dBm]"

        param_dict_path = path + r"\param_dict.json"
        with open(param_dict_path) as f:
            param_dict = json.load(f)

        title = (
            f"ro_freq={param_dict['ro_freq']*1e-9}GHz, "
            + f"current={param_dict['current']*1e3}mA"
        )

        fig = mag_phase_1D_plot(mag1D, phase1D, ro_power, xlabel, title)
        fig.tight_layout()
        fig.savefig(f"{path}/1D_vs_ro_power.png", bbox_inches="tight")
# plot 1p5D vs ro_power
if not freq_npts == 1:
    if param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == "ro_power":
        filename = path + r"\data.ddh5"
        h5file = h5py.File(filename, "r")
        mag2D = np.array(h5file["data"]["mag_dB"][::])
        mag2D = offset_for_1p5D_plot(mag2D)
        phase2D = np.array(h5file["data"]["phase"][::])
        phase2D = np.array([flatten_phase(phase2D[i, :]) for i in range(len(phase2D))])
        phase2D = offset_for_1p5D_plot(phase2D)
        ro_freq = np.array(h5file["data"]["ro_freq"][0]) * 1e-9  # [GHz]
        ro_power = np.array(h5file["data"]["ro_power"][::])
        xlabel = "Readout frequency [GHz]"
        ylabel = "Readout power [dBm]"

        param_dict_path = path + r"\param_dict.json"
        with open(param_dict_path) as f:
            param_dict = json.load(f)

        title = f"current={param_dict['current']*1e3}mA"

        fig = mag_phase_1p5D_plot(
            mag2D, phase2D, ro_freq, ro_power, xlabel, ylabel, title
        )
        fig.tight_layout()
        fig.savefig(f"{path}/1p5D_vs_ro_power.png", bbox_inches="tight")

# plot 2D vs ro_freq vs ro_power
if not freq_npts == 1:
    if param_dict["CW_twotone_sweep_ro_freq"]["sweep"] == "ro_power":
        filename = path + r"\data.ddh5"
        h5file = h5py.File(filename, "r")
        mag2D = np.array(h5file["data"]["mag_dB"][::])
        phase2D = np.array(h5file["data"]["phase"][::])
        phase2D = np.array([flatten_phase(phase2D[i, :]) for i in range(len(phase2D))])
        ro_freq = np.array(h5file["data"]["ro_freq"][0]) * 1e-9  # [GHz]
        ro_power = np.array(h5file["data"]["ro_power"][:])  # [mA]
        xlabel = "Readout frequency [GHz]"
        ylabel = "Readout power [dBm]"

        param_dict_path = path + r"\param_dict.json"
        with open(param_dict_path) as f:
            param_dict = json.load(f)

        title = f"current={param_dict['current']*1e3}mA"

        fig = mag_phase_2D_plot(
            mag2D, phase2D, ro_freq, ro_power, xlabel, ylabel, title
        )
        fig.tight_layout()
        fig.savefig(f"{path}/2D_vs_ro_power.png", bbox_inches="tight")


# copy the directory to the server
copy_tree(filepath_parent, new_path)

plt.show()
