"""
for fluxonium measurement.
CW twotone with VNA and HDAWG for pulsed-drive.
@Taketo
"""

import datetime
import os
import sys
import time

import h5py
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from helpers.CW_Setup import db_path, param_dict, pd_file, setup_file, vna_IP, yoko_IP
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from laboneq.simple import *
from qcodes.instrument_drivers.rohde_schwarz import RohdeSchwarzZNB8
from qcodes.instrument_drivers.yokogawa import YokogawaGS200
from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A
from tqdm import tqdm

sys.path.append("../analysis_code")
from spectroscopy_1D_plot import spectroscopy_1D_plot
from spectroscopy_2D_plot import spectroscopy_2D_plot

exp_name = "CW_pulsed_twotone"
tags = ["0_CW-pulsed twotone"]

# define qubit drive frequency list
freq_start = param_dict["CW_pulsed_twotone"]["qu_freq_start"]
freq_stop = param_dict["CW_twotone"]["qu_freq_stop"]
if param_dict["CW_twotone"]["qu_freq_npts"] == False:
    freq_npts = (
        int((freq_stop - freq_start) / param_dict["CW_twotone"]["qu_freq_step"]) + 1
    )
else:
    freq_npts = param_dict["CW_twotone"]["qu_freq_npts"]
freq_list = np.linspace(freq_start, freq_stop, freq_npts)

# define datadict
if param_dict["CW_twotone"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        qu_freq=dict(unit="sec"),
        time=dict(),
        mag_dB=dict(axes=["qu_freq", "time"], unit="dB"),
        phase=dict(axes=["qu_freq", "time"], unit="rad"),
    )
    datadict.validate()
elif param_dict["CW_twotone"]["sweep"] == "current":
    exp_name = exp_name + "_vs_" + "flux"
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["sweep"]] = "sweeping"
    sweep_list = np.linspace(
        param_dict["sweep_start"], param_dict["sweep_stop"], param_dict["sweep_npts"]
    )
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        qu_freq=dict(unit="sec"),
        current=dict(unit="A"),
        time=dict(),
        mag_dB=dict(axes=["qu_freq", "current", "time"], unit="dB"),
        phase=dict(axes=["qu_freq", "current", "time"], unit="rad"),
    )
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["sweep"]] = "sweeping"
    sweep_list = np.linspace(
        param_dict["sweep_start"], param_dict["sweep_stop"], param_dict["sweep_npts"]
    )
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="sec"),
        sweep_param=dict(unit="dBm"),
        time=dict(),
        mag_dB=dict(axes=["qu_freq", "sweep_param", "time"], unit="dB"),
        phase=dict(axes=["qu_freq", "sweep_param", "time"], unit="rad"),
    )
    datadict.validate()

with DDH5Writer(datadict, db_path, name=exp_name) as writer:
    filepath_parent = writer.filepath.parent
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, pd_file])
    writer.save_text("directry_path.md", f"{filepath_parent}")

    # connect to the equipment
    vna = RohdeSchwarzZNB8("VNA", vna_IP, init_s_params=False)
    gs = YokogawaGS200("gs200", yoko_IP)
    sc = SC5521A("mw1")

    # setting of VNA
    vna.add_channel("S21")
    vna.cont_meas_on()
    vna.display_single_window()
    vna.channels.S21.sweep_type("CW_Point")
    vna.channels.S21.power.set(-50)  # for safety

    vna.rf_on()
    for sweep_param in tqdm(sweep_list):
        # update param_dict
        if not param_dict["sweep"] == False:
            param_dict[param_dict["sweep"]] = sweep_param

        ## update parameters
        # setting of VNA
        vna.channels.S21.cw_frequency(param_dict["ro_freq"])
        vna.channels.S21.power.set(param_dict["ro_power"])
        vna.channels.S21.npts(1)  # maybe same thing as average
        vna.channels.S21.bandwidth(param_dict["vna_bw"])
        vna.channels.S21.avg(param_dict["vna_avg"])

        # setting of Yokogawa
        gs.voltage_limit(param_dict["gs_voltage_lim"])
        gs.current_range(param_dict["gs_current_range"])
        gs.ramp_current(
            param_dict["current"], param_dict["gs_rampstep"], param_dict["gs_delay"]
        )
        time.sleep(0.75)  # wait for the current reaching at the target

        # setting of Signal Core
        sc.power(param_dict["qu_power"])

        mag_dB_array = np.zeros(freq_npts)
        # measurement
        for idx, qu_freq in enumerate(freq_list):
            sc.frequency(qu_freq)
            # time.sleep(0.25)
            vna.channels.S21.autoscale()
            mag_dB, phase = vna.channels.S21.point_fixed_frequency_db_phase.get()
            mag_dB_array[idx] = mag_dB

            # record the measurement time (in YYYYMMDDhhmmss format)
            now = datetime.datetime.now()
            time = int(now.strftime("%Y%m%d%H%M%S"))

            # save the data
            if param_dict["CW_twotone"]["sweep"] == False:
                writer.add_data(
                    qu_freq=freq_list, time=time, mag_dB=mag_dB, phase=phase
                )

            elif param_dict["CW_twotone"]["sweep"] == "current":
                writer.add_data(
                    qu_freq=freq_list,
                    current=sweep_param,
                    time=time,
                    mag_dB=mag_dB,
                    phase=phase,
                )

            else:
                writer.add_data(
                    qu_freq=freq_list,
                    sweep__param=sweep_param,
                    time=time,
                    mag_dB=mag_dB,
                    phase=phase,
                )

        # plot the single trace
        if param_dict["CW_twotone"]["sweep"] == False:
            fig_fit, f0, fwhm = spectroscopy_1D_plot(
                freq_list, 10 ** (mag_dB_array / 20)
            )
            fig_fit.suptitle(f"Qubit drive power: {param_dict["qu_power"]}dBm")
            fig_fit.savefig(
                f"{writer.filepath.parent}/qu_power_{param_dict["qu_power"]}dBm_fit.png",
                bbox_inches="tight",
            )
            writer.save_text(
                f"fitted_resonator_freq_at_qu_power_{param_dict["qu_power"]}dBm.md",
                f"fitted_qubit_freq:{f0} Hz",
            )
    vna.rf_off()
    vna.clear_channels()
    vna.close()
    gs.close()

# 2D plot
if param_dict["CW_twotone"]["sweep"] == False:
    pass
elif param_dict["CW_twotone"]["sweep"] == "current":
    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    qu_freq = h5file["data"]["qu_freq"][0][:] * 1e-9
    current = h5file["data"]["current"][:] * 1e6
    mag_dB = np.array(h5file["data"]["mag_dB"][:][:]).T
    fig_2D_plot, __ = spectroscopy_2D_plot(
        x_axis=current,
        y_axis=qu_freq,
        spectroscopy_data=mag_dB,
        x_axis_label="Current [uA]",
        y_axis_label="Drive frequency [GHz]",
        z_axis_label="Magnitude [dB]",
        normalization=False,
    )
    fig_2D_plot.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches="tight")

else:
    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    ro_freq = h5file["data"]["qu_freq"][0][:] * 1e-9
    sweep_param = h5file["data"]["sweep_param"][:]
    mag_dB = np.array(h5file["data"]["mag_dB"][:][:])
    fig_2D_plot, __ = spectroscopy_2D_plot(
        x_axis=qu_freq,
        y_axis=sweep_param,
        spectroscopy_data=mag_dB,
        x_axis_label="Drive frequency [GHz]",
        y_axis_label=param_dict["CW_twotone"]["sweep"],
        z_axis_label="Magnitude [dB]",
        normalization=False,
    )
    fig_2D_plot.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches="tight")
