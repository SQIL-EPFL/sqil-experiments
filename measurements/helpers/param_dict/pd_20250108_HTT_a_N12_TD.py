import sys

import numpy as np

sys.path.append(r"Z:\Projects\HighTempFluxonium\Measurement\measurement_codes\helpers")
from utilities import logsweep

pd_file = __file__


ro_freq = 3e9  # [Hz] SHFQC output
qu_freq = 4.6815e9  # [Hz]
gf_by2_freq = 4.604e9  # [Hz]
freq_03 = 13.40e9

# qu_freq = 4.72985e9 #[Hz]
gf_by2_freq = 4.604e9  # [Hz]

two_chi = 13.6e6  # [Hz]

pi_pulse = 71.4e-9
T1 = 6e-6
T2 = 3e-6

param_dict = {
    "ro_freq": 3e9,  # SHFQA output frequency[Hz]
    "ro_lo_freq": 2.6e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_power": 0,  # [dBm] ZInstrument output power
    "ro_acquire_range": -10,
    # external LO source (Signal core)
    "ro_exLO_freq": 17.34e9,  # external LO freq [GHz]
    "ro_exLO_power": 15,  # [dBm]
    "qu_freq": qu_freq,
    "qu_lo_freq": 4.4e9,  # [GHz]
    "qu_pi_pulse_length": pi_pulse,
    "qu_power": -10,
    "ef_pulse_length": 10e-6,
    # "ef_lo_freq":5.6e9, # cannot use different lo freq for the same output line!
    "ef_drive_power": 0,  # maybe need to be lower than "qu_power"(second tone). need to be fixed.
    "current": 0e-3,  # [A]
    # pulsed onetone
    "pulsed_onetone": {
        "ro_freq_step": 1e6,  # [Hz]
        "ro_freq_start": ro_freq - 100e6,  # [Hz]
        "ro_freq_stop": ro_freq + 100e6,  # [Hz] must be larger than start
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "ro_pulse_length": 4e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "reset_delay": 0.1e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 14,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed twotone
    "pulsed_twotone": {
        "qu_freq_step": 1e6,  # [Hz]
        "qu_freq_start": qu_freq - 4 * two_chi,  # [Hz]
        "qu_freq_stop": qu_freq + 4 * two_chi,  # [Hz] must be larger than start
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "qu_pulse_length": 2000e-9,  # [sec]
        "reset_delay": 0.1e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 16,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # time rabi
    "time_rabi": {
        "qu_pulse_length_step": False,
        "qu_pulse_length_start": 1e-10,
        "qu_pulse_length_stop": 400e-9,
        "qu_pulse_length_npts": 150,
        "sweep": "qu_freq",  # "current", # str. name of the sweep parameter
        "reset_delay": 30e-6,  # > 3*T1
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # T1
    "T1": {
        "delay_sweep_start": 1e-10,
        "delay_sweep_stop": 100e-6,
        "delay_sweep_npts": 31,
        "logsweep": True,
        "delay_sweep_list": np.hstack(
            [np.linspace(0, 15e-6, 16), logsweep(16e-6, 60e-6, 11)]
        ),
        "sweep": False,  # "current", # str. name of the sweep parameter
        "reset_delay": 110e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # Ramsey
    "ramsey": {
        "interval_sweep_start": 1e-10,
        "interval_sweep_stop": 20e-6,
        "interval_sweep_npts": 61,
        "sweep": False,  # "current", # str. name of the sweep parameter
        "reset_delay": 50e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # T2 echo
    "echo": {
        "interval_sweep_start": 1e-10,
        "interval_sweep_stop": 40e-6,
        "interval_sweep_npts": 31,
        "logsweep": True,
        "interval_sweep_list": np.hstack(
            [np.linspace(0, 7e-6, 16), logsweep(7.1e-6, 50e-6, 16)]
        ),
        "sweep": False,  # "current", # str. name of the sweep parameter
        "reset_delay": 60e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 2,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # interleaved T1 T2echo
    "interleaved": {
        # for T1
        "delay_sweep_list": np.linspace(1e-10, 100e-6, 31),
        # for T2 echo
        "interval_sweep_list": np.linspace(1e-10, 100e-6, 31),
        "index_num": 1000,
        "reset_delay": 110e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": False,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": False,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed threetone
    "pulsed_threetone": {
        "ef_freq_step": 0.1e6,
        "ef_freq_start": 4.335e9,
        "ef_freq_stop": 4.35e9,
        "ef_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "ef_pulse_length": 10e-6,
        "reset_delay": 80e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 14,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # dispersive shift
    "dispersive_shift": {
        "ro_freq_step": 0.25e6,  # [Hz]
        "ro_freq_start": 20.3e9,  # [Hz]
        "ro_freq_stop": 20.4e9,  # [Hz] must be larger than start
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "ro_pulse_length": 4e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 14,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    "qu_freq_detune": 0.8e6,  # [Hz] used only for ramsey measurement
    "pi_pulse_rep": 1,  # N pi pulses in T2 Echo measurement
    "readout_delay": 0e-9,  # time interval between pulse sequence and the readout
    "acquire_delay": 0e-9,
    "reset_delay": 100e-6,  # [sec]
    "avg": 2**15,  # [#]
    "external_avg": 1,  # [#]
    "save_pulsesheet": True,
    # yokogawa setting
    # "gs_rampstep":1e-6,
    # "gs_delay":5000e-6,
    # "gs_voltage_lim": 5, # [V]
    # "gs_current_range": 10e-3,
    # sweep list
    "sweep_start": 2e9,
    "sweep_stop": 6e9,
    "sweep_npts": 41,
    "sweep_list": False,
    # "sweep_start":4.734e9-40e6,
    # "sweep_stop":4.734e9+40e6,
    # "sweep_npts":81,
    # "sweep_list":False,
}
""" Note
"qu_freq_01": 4.7317e9,
"""
