"""
Equipment:
    ZI SHFQC for readout
    ZI SHFQC for qubit drive
"""

import matplotlib.pyplot as plt
import numpy as np
from dispersive_shift_ef_exp import main_exp, setup_file
from helpers.TD_setup_left_line import db_path, descriptor_file, main_descriptor
from helpers.utilities import (
    analyze_qspec,
    external_average_loop_dispersive_ef,
    sparameter_to_dB_phase,
)
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

exp_name = "dispersive_shift_ef"
tags = ["0_dispersive_shift_ef"]

param_dict = {
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_freq_start": 7.540e9,
    "ro_freq_stop": 7.575e9,
    "ro_freq_npts": 101,
    "ro_lo_freq": 7.1e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_power": -30,
    "ro_acquire_range": -5,
    "qu_pi_pulse_length": 64e-9,
    "qu_freq": 6186646414,
    "qu_lo_freq": 5.7e9,
    "qu_drive_power": 9.18,  # dBm < 26.99dBm
    "ef_pi_pulse_length": 131e-9,
    "ef_freq": 5857932046,
    "ef_drive_power": 9.55,
    "reset_delay": 50e-6,  # [sec]
    "avg": 2**14,
    "external_avg": 1,
    "save_pulsesheet": True,
}

ro_freq_sweep = np.linspace(
    param_dict["ro_freq_start"], param_dict["ro_freq_stop"], param_dict["ro_freq_npts"]
)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    ro_freq=dict(unit="Hz"),
    ground_data=dict(axes=["ro_freq"], unit=""),
    excited_data=dict(axes=["ro_freq"], unit=""),
)
datadict.validate()

with DDH5Writer(datadict, db_path, name=exp_name) as writer:
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, descriptor_file])
    writer.save_text("directry_path.md", f"{writer.filepath.parent}")

    # create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)

    exp = main_exp(session, param_dict, writer)
    compiled_exp = session.compile(exp)

    # output and save a pulse sheet
    if param_dict["save_pulsesheet"] == True:
        show_pulse_sheet(
            f"{writer.filepath.parent}/dispersive_shift_ef_pulsesheet",
            compiled_exp,
            interactive=False,
        )

    # run the experiment and take external averages
    data0, data1 = external_average_loop_dispersive_ef(
        session,
        compiled_exp,
        param_dict["external_avg"],
    )

    # save the data in DDH5 file
    writer.add_data(ro_freq=ro_freq_sweep, excited_data=data0, f_state_data=data1)

    # plot magnitude (dB)
    plt.figure()
    plt.plot(
        ro_freq_sweep * 1e-9, 20 * np.log10(np.abs(data0)), label="e-state", color="red"
    )
    plt.plot(
        ro_freq_sweep * 1e-9,
        20 * np.log10(np.abs(data1)),
        label="f-state",
        color="gold",
    )
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude [dB]")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_mag.png", bbox_inches="tight"
    )
    # plot magnitude difference(dB)
    plt.figure()
    plt.plot(
        ro_freq_sweep * 1e-9,
        20 * np.log10(np.abs(data0)) - 20 * np.log10(np.abs(data1)),
        label="e - f",
        color="green",
    )
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude [dB]")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_mag_difference.png",
        bbox_inches="tight",
    )

    # plot magnitude (dB)
    plt.figure()
    plt.plot(ro_freq_sweep * 1e-9, np.abs(data0), label="e-state", color="red")
    plt.plot(ro_freq_sweep * 1e-9, np.abs(data1), label="f-state", color="gold")
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude [arb]")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_linmag.png", bbox_inches="tight"
    )
    # plot magnitude difference(dB)
    plt.figure()
    plt.plot(
        ro_freq_sweep * 1e-9,
        np.abs(data0) - np.abs(data1),
        label="e - f",
        color="green",
    )
    plt.xlabel("Readout frequency [GHz]")
    plt.ylabel("Magnitude [arb]")
    plt.title("Dispersive shift")
    plt.legend()
    plt.savefig(
        f"{writer.filepath.parent}/dispersive_shift_linmag_difference.png",
        bbox_inches="tight",
    )


if param_dict["plot_1D"] == True:
    # reload all data after writer-object is released
    filename = os.path.join(filepath_parent, "data.ddh5")
    h5file = h5py.File(filename, "r")

    ro_freq = h5file["data"]["ro_freq"][:]

    excited_data = h5file["data"]["excited_data"][:]
    ground_data = h5file["data"]["ground_data"][:]
    fig_1D_plot, res_freq_multi, FWHM_multi = spectroscopy_1D_plot_multitrace(
        ro_freq,
        [excited_data, f_state_data],
        ["e-state", "f-state"],
        "RO Frequency [Hz]",
        "Mag []",
        ["blue", "red"],
    )

    fig_1D_plot.suptitle("Dispersive Shift")
    fig_1D_plot.savefig(f"{filepath_parent}/1D_plot.png", bbox_inches="tight")

    with open(str(filepath_parent) + "/fitted_parameters.md", "w+") as f:
        f.write("freq e-state[Hz]: " + str(int(res_freq_multi[0])) + "\n")
        f.write("freq f-state[Hz]: " + str(int(res_freq_multi[1])) + "\n")
        chi_ef = res_freq_multi[1] - res_freq_multi[0]
        f.write("chi-ef[Hz]: " + str(int(chi)) + "\n")
