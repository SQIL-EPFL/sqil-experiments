"""
Dummy one tone measurement code for checking phase stability of VNA
@Taketo
"""

import datetime
import os
import sys
import time

import h5py
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import tqdm
from scipy.optimize import curve_fit, minimize, newton

sns.set()
colors = sns.color_palette("hls", 10)
sns.set(palette=colors)
sns.set_context("talk")
sns.set_style("whitegrid")
sns.set_style("ticks")
from helpers.customized_drivers.Rohde_Schwarz_ZNA26 import RohdeSchwarzZNA26
from helpers.customized_drivers.ZNB_taketo import RohdeSchwarzZNBChannel
from helpers.setup.CW_Setup import (
    db_path,
    param_dict,
    pd_file,
    setup_file,
    vna_IP,
    yoko_IP,
)
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from qcodes.instrument_drivers.yokogawa import YokogawaGS200

sys.path.append("../analysis_code")
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
elif param_dict["CW_onetone"]["sweep"] == "current":
    exp_name = exp_name + "_vs_" + "flux"
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["CW_onetone"]["sweep"]] = "sweeping"
    sweep_list = np.linspace(
        param_dict["sweep_start"], param_dict["sweep_stop"], param_dict["sweep_npts"]
    )
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="Hz"),
        current=dict(unit="A"),
        # timestamp=dict(),
        # mag_dB=dict(axes=["ro_freq","current","timestamp"],
        #             unit="dB"),
        # phase=dict(axes=["ro_freq","current","timestamp"],
        #            unit="rad")
        mag_dB=dict(axes=["ro_freq", "current"], unit="dB"),
        phase=dict(axes=["ro_freq", "current"], unit="rad"),
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
        # timestamp=dict(),
        # mag_dB=dict(axes=["ro_freq","ro_power","timestamp"],
        #             unit="dB"),
        # phase=dict(axes=["ro_freq","ro_power","timestamp"],
        #            unit="rad")
        mag_dB=dict(axes=["ro_freq", "ro_power"], unit="dB"),
        phase=dict(axes=["ro_freq", "ro_power"], unit="rad"),
    )
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["CW_onetone"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["CW_onetone"]["sweep"]] = "sweeping"
    sweep_list = np.linspace(
        param_dict["sweep_start"], param_dict["sweep_stop"], param_dict["sweep_npts"]
    )
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        ro_freq=dict(unit="Hz"),
        sweep_param=dict(unit=""),
        # timestamp=dict(),
        # mag_dB=dict(axes=["ro_freq","sweep_param","timestamp"],
        #             unit="dB"),
        # phase=dict(axes=["ro_freq","sweep_param","timestamp"],
        #            unit="rad")
        mag_dB=dict(axes=["ro_freq", "sweep_param"], unit="dB"),
        phase=dict(axes=["ro_freq", "sweep_param"], unit="rad"),
    )
    datadict.validate()

with DDH5Writer(datadict, db_path, name=exp_name) as writer:
    filepath_parent = writer.filepath.parent
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, pd_file])
    writer.save_text("directry_path.md", f"{filepath_parent}")

    # connect to the equipment
    vna = RohdeSchwarzZNA26(
        "VNA",
        vna_IP,
        init_s_params=False,
        reset_channels=False,
    )
    # gs = YokogawaGS200("gs200", yoko_IP)

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
    vna.channels.S21.sweep_type("CW_Point")
    vna.channels.S21.power.set(-50)  # for safety

    vna.rf_on()
    for sweep_param in tqdm.tqdm(sweep_list):
        # update param_dict
        if not param_dict["CW_onetone"]["sweep"] == False:
            param_dict[param_dict["CW_onetone"]["sweep"]] = sweep_param

        ## update parameters
        # setting of VNA
        vna.channels.S21.cw_frequency(freq_start)
        vna.channels.S21.npts(1)  # maybe same thing as average
        vna.channels.S21.power.set(param_dict["ro_power"])
        vna.channels.S21.bandwidth(param_dict["vna_bw"])
        vna.channels.S21.avg(param_dict["vna_avg"])

        # setting of Yokogawa
        # gs.voltage_limit(param_dict["gs_voltage_lim"])
        # gs.current_range(param_dict["gs_current_range"])
        # gs.ramp_current(param_dict["current"],
        #                 param_dict["gs_rampstep"],
        #                 param_dict["gs_delay"])
        # time.sleep(5) # wait for the current reaching at the target
        # Actually, VNA waits to start measurement until yokogawa reaches at the target current (checked by Taketo)

        # measurement
        # mag_dB, phase =vna.channels.S21.trace_db_phase.get()
        mag_dB, phase = vna.channels.S21.point_fixed_frequency_db_phase.get()
        # save the data
        if param_dict["CW_onetone"]["sweep"] == False:
            writer.add_data(
                ro_freq=freq_list,
                # timestamp=timestamp,
                mag_dB=mag_dB,
                phase=phase,
            )

        elif param_dict["CW_onetone"]["sweep"] == "current":
            writer.add_data(
                ro_freq=freq_list,
                current=sweep_param,
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
                sweep__param=sweep_param,
                # timestamp=timestamp,
                mag_dB=mag_dB,
                phase=phase,
            )

        # # plot the single trace
        # if param_dict["CW_onetone"]["sweep"]==False:
        #     # fitting
        #     fig_fit, f0, fwhm = spectroscopy_1D_plot(freq_list, 10**(mag_dB/20))
        #     fig_fit.suptitle(f"RO Power: {param_dict['ro_power']}dBm")
        #     fig_fit.savefig(f"{writer.filepath.parent}/ro_power_{param_dict['ro_power']}dBm_fit.png", bbox_inches='tight')
        #     writer.save_text(f"fitted_resonator_freq_at_ro_power_{param_dict['ro_power']}dBm.md", f'fitted_resonator_freq:{f0} Hz')

        #     # magnitude and phase plotting
        #     fig_db_phase = plt.figure(figsize=(15,12))
        #     ro_freq = freq_list*1e-9
        #     ax_mag = fig_db_phase.add_subplot(311)
        #     ax_phase = fig_db_phase.add_subplot(312)
        #     ax_calphase = fig_db_phase.add_subplot(313)
        #     ax_mag.plot(ro_freq,mag_dB)
        #     ax_phase.plot(ro_freq, phase)
        #     fig_db_phase.suptitle(f"One tone @ {param_dict['ro_power']} dBm")
        #     # ax_mag.set_xlabel(r"Frequency [$\mathrm{GHz}$]")
        #     ax_mag.set_ylabel(r"Magnitude [$\mathrm{dB}$]")
        #     ax_calphase.set_xlabel(r"Frequency [$\mathrm{GHz}$]")
        #     ax_phase.set_ylabel(r"Unwrapped phase [rad]")
        #     ax_calphase.set_ylabel(r"Calibrated phase [rad]")
        #     ax_mag.grid(visible=True, which="both", axis="both")
        #     ax_phase.grid(visible=True, which="both", axis="both")
        #     ax_calphase.grid(visible=True, which="both", axis="both")

        #     # remove the unwrapped phase gradient
        #     # simple guess
        #     slope = (phase[-1]-phase[0])/(ro_freq[-1]-ro_freq[0])
        #     offset = phase[0]-slope*ro_freq[0]
        #     def func(freq,slope,offset):
        #         return slope*freq + offset

        #     popt, pcov = curve_fit(f=func,
        #                    xdata=ro_freq,
        #                    ydata=phase,
        #                    p0 = [slope, offset], # initial value
        #                    )
        #     fit_slope, fit_offset = popt
        #     calibrated_phase=phase-slope*ro_freq-fit_offset
        #     ax_calphase.plot(ro_freq, calibrated_phase)
        #     fig_db_phase.savefig(f"{filepath_parent}/1D_plot.png", bbox_inches='tight')

    vna.rf_off()
    # vna.clear_channels()
    vna.close()

    # gs.ramp_current(0,
    #             param_dict["gs_rampstep"],
    #             param_dict["gs_delay"])
    # gs.close()

# # 1D plot at fixed frequency
# if freq_npts==1:
#     if param_dict["CW_onetone"]["sweep"]==False:
#         pass
#     elif param_dict["CW_onetone"]["sweep"]=="current":
#         #reload all data after writer-object is released
#         filename = os.path.join(filepath_parent, 'data.ddh5')
#         h5file = h5py.File(filename,"r")

#         ro_freq = h5file["data"]["ro_freq"][0]*1e-9
#         current = h5file["data"]["current"][:]*1e6
#         mag_dB = np.array(h5file["data"]["mag_dB"][:][:]).T
#         phase = np.unwrap(np.array(h5file["data"]["phase"]))
#         fig = plt.figure(figsize=(15,8))
#         ax_mag = fig.add_subplot(121)
#         ax_phase = fig.add_subplot(122)
#         ax_mag.plot(current,mag_dB)
#         ax_phase.plot(current, phase)
#         fig.suptitle(f"Flux sweep @ {ro_freq} GHz")
#         ax_mag.set_xlabel(r"Current [$\mathrm{\mu A}$]")
#         ax_mag.set_ylabel(r"Magnitude [$\mathrm{dB}$]")
#         ax_phase.set_xlabel(r"Current [$\mathrm{\mu A}$]")
#         ax_phase.set_ylabel(r"Phase [rad]")
#         ax_mag.grid(visible=True, which="both", axis="both")
#         ax_phase.grid(visible=True, which="both", axis="both")
#         fig.savefig(f"{filepath_parent}/1D_plot.png", bbox_inches='tight')

#     elif param_dict["CW_onetone"]["sweep"]=="ro_power":
#         #reload all data after writer-object is released
#         filename = os.path.join(filepath_parent, 'data.ddh5')
#         h5file = h5py.File(filename,"r")

#         ro_freq = h5file["data"]["ro_freq"][0]*1e-9
#         ro_power = h5file["data"]["ro_power"][:]
#         mag_dB = np.array(h5file["data"]["mag_dB"][:][:]).T
#         phase = np.unwrap(np.array(h5file["data"]["phase"]))
#         fig = plt.figure(figsize=(15,8))
#         ax_mag = fig.add_subplot(121)
#         ax_phase = fig.add_subplot(122)
#         ax_mag.plot(current,mag_dB)
#         ax_phase.plot(current, phase)
#         fig.suptitle(f"Flux sweep @ {ro_freq} GHz")
#         ax_mag.set_xlabel(r"Readout power [$\mathrm{dBm}$]")
#         ax_mag.set_ylabel(r"Magnitude [$\mathrm{dB}$]")
#         ax_phase.set_xlabel(r"Readout power [$\mathrm{dBm}$]")
#         ax_phase.set_ylabel(r"Phase [rad]")
#         ax_mag.grid(visible=True, which="both", axis="both")
#         ax_phase.grid(visible=True, which="both", axis="both")
#         fig.savefig(f"{filepath_parent}/1D_plot.png", bbox_inches='tight')

#     else:
#         #reload all data after writer-object is released
#         filename = os.path.join(filepath_parent, 'data.ddh5')
#         h5file = h5py.File(filename,"r")

#         ro_freq = h5file["data"]["ro_freq"][0]*1e-9
#         sweep_param = h5file["data"]["sweep_param"][:]
#         mag_dB = np.array(h5file["data"]["mag_dB"][:][:]).T
#         phase = np.unwrap(np.array(h5file["data"]["phase"]))
#         fig = plt.figure(figsize=(15,8))
#         ax_mag = fig.add_subplot(121)
#         ax_phase = fig.add_subplot(122)
#         ax_mag.plot(current,mag_dB)
#         ax_phase.plot(current, phase)
#         fig.suptitle(f"Flux sweep @ {ro_freq} GHz")
#         ax_mag.set_xlabel(f'{param_dict["CW_onetone"]["sweep"]}')
#         ax_mag.set_ylabel(r"Magnitude [$\mathrm{dB}$]")
#         ax_phase.set_xlabel(f'{param_dict["CW_onetone"]["sweep"]}')
#         ax_phase.set_ylabel(r"Phase [rad]")
#         ax_mag.grid(visible=True, which="both", axis="both")
#         ax_phase.grid(visible=True, which="both", axis="both")
#         fig.savefig(f"{filepath_parent}/1D_plot.png", bbox_inches='tight')

# # 2D plot
# else:
#     if param_dict["CW_onetone"]["sweep"]==False:
#         pass
#     elif param_dict["CW_onetone"]["sweep"]=="current":
#         #reload all data after writer-object is released
#         filename = os.path.join(filepath_parent, 'data.ddh5')
#         h5file = h5py.File(filename,"r")

#         ro_freq = h5file["data"]["ro_freq"][0][:]*1e-9
#         current = h5file["data"]["current"][:]*1e6
#         mag_dB = np.array(h5file["data"]["mag_dB"][:][:]).T
#         fig_2D_plot, __ = spectroscopy_2D_plot(x_axis=current,
#                              y_axis=ro_freq,
#                              spectroscopy_data=mag_dB,
#                              x_axis_label="Current [uA]",
#                              y_axis_label="Readout frequency [GHz]",
#                              z_axis_label="Magnitude [dB]",
#                              normalization=False)
#         fig_2D_plot.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches='tight')

#     elif param_dict["CW_onetone"]["sweep"]=="ro_power":
#         #reload all data after writer-object is released
#         filename = os.path.join(filepath_parent, 'data.ddh5')
#         h5file = h5py.File(filename,"r")

#         ro_freq = h5file["data"]["ro_freq"][0][:]*1e-9
#         ro_power = h5file["data"]["ro_power"][:]
#         mag_dB = np.array(h5file["data"]["mag_dB"][:][:])
#         fig_2D_plot, __ = spectroscopy_2D_plot(x_axis=ro_freq,
#                              y_axis=ro_power,
#                              spectroscopy_data=mag_dB,
#                              x_axis_label="Readout frequency [GHz]",
#                              y_axis_label="Readout power [dBm]",
#                              z_axis_label="Magnitude [dB]",
#                              normalization=False)
#         fig_2D_plot.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches='tight')

#     else:
#         #reload all data after writer-object is released
#         filename = os.path.join(filepath_parent, 'data.ddh5')
#         h5file = h5py.File(filename,"r")

#         ro_freq = h5file["data"]["ro_freq"][0][:]*1e-9
#         sweep_param = h5file["data"]["sweep_param"][:]
#         mag_dB = np.array(h5file["data"]["mag_dB"][:][:])
#         fig_2D_plot, __ = spectroscopy_2D_plot(x_axis=ro_freq,
#                              y_axis=sweep_param,
#                              spectroscopy_data=mag_dB,
#                              x_axis_label="Readout frequency [GHz]",
#                              y_axis_label=param_dict["CW_onetone"]["sweep"],
#                              z_axis_label="Magnitude [dB]",
#                              normalization=False)
#         fig_2D_plot.savefig(f"{filepath_parent}/2D_plot.png", bbox_inches='tight')
