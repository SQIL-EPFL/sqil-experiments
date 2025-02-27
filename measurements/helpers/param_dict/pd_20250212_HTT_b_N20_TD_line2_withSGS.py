import sys

import numpy as np

sys.path.append(r"Z:\Projects\HighTempFluxonium\Measurement\measurement_codes\helpers")
from utilities import logsweep

pd_file = __file__


ro_freq = 3.797e9  # [Hz]
ro_freq_e = 3.7993e9  # [Hz] # measuring |e> state
# qu_freq = 4.67444e9 #[Hz]
qu_freq = 6.4813e9  # [Hz]
qu_freq_12 = 6.211e9
qu_freq02_by2 = 6.346e9
freq_03 = 18.6086e9


# two_chi = 13.6e6 #[Hz]

pi_pulse = 74.4e-9
qu_power = 9.55
# pi_pulse = 5783.8e-9
# qu_power = -27


T1 = 160e-6
T2 = 160e-6


param_dict = {
    "ro_freq": ro_freq,  # [Hz] SHFQC output frequenc2.6
    "ro_lo_freq": 3.4e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_power": 0,  # [dBm] ZInstrument output power
    "ro_acquire_range": -20,
    # external LO source (Signal core)
    "ro_exLO_freq": 17.1e9,  # This freq cannot be detuned by more than 500MHz from "ro_freq"
    "ro_exLO_power": 12.5,  # [dBm]
    "qu_freq": qu_freq,
    # "qu_lo_freq":6e9, #[GHz]
    "qu_pi_pulse_length": 74.4e-9,
    "qu_power": 6.99,  # HDAWG output power in dBm
    "SGS_power": 10,
    # "SGS_freq":6e9,
    "sideslope_length": 50e-9,
    "ef_freq": qu_freq_12,
    "ef_pulse_length": 42.4e-9,
    "ef_drive_power": 9.55,  # maybe need to be lower than "qu_power"(second tone). need to be fixed.
    "current": 0e-3,  # [A]
    # pulsed onetone
    "pulsed_onetone": {
        "ro_freq_step": 0.1e6,  # [Hz]
        "ro_freq_start": ro_freq - 200e6,  # [Hz]
        "ro_freq_stop": ro_freq + 200e6,  # [Hz] must be larger than start
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "ro_power",#"current", # str. name of the sweep parameter
        "ro_pulse_length": 2e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "reset_delay": 0.1e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 10000,  # 10000, # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed twotone
    "pulsed_twotone": {
        "qu_freq_step": 1e6,  # [Hz]
        "qu_freq_start": qu_freq + 100e6,  # [Hz]
        "qu_freq_stop": qu_freq - 100e6,  # [Hz] must be larger than start
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "qu_power": 0,
        "qu_pi_pulse_length": 2000e-9,  # [sec]
        "reset_delay": 0.1e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 10000,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # time rabi
    "time_rabi": {
        "qu_pulse_length_step": False,
        "qu_pulse_length_start": 1e-10,
        "qu_pulse_length_stop": 1000e-9,
        "qu_pulse_length_npts": 61,
        "sweep": False,  # "SGS_power",#"current", # str. name of the sweep parameter
        # "qu_power":,
        # "qu_freq":qu_freq+10e6,
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 2
        ** 13,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # amp rabi
    "amp_rabi": {
        "qu_pulse_amp_step": False,
        "qu_pulse_amp_start": 0,
        "qu_pulse_amp_stop": 1,
        "qu_pulse_amp_npts": 51,
        "sweep": False,  # "current", # str. name of the sweep parameter
        "qu_power_range": 10,  ## ONLY for AMP RABI
        # "ro_pulse_length":15e-6, #[sec]
        # "qu_pi_pulse_length":70e-9,
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 2
        ** 12,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # T1
    "T1": {
        "delay_sweep_start": 1e-10,
        "delay_sweep_stop": 3 * T1,
        "delay_sweep_npts": 100,
        "logsweep": True,
        "delay_sweep_list": np.hstack(
            [np.linspace(0, T1, 11), logsweep(T1 * 1.1, 5 * T1, 11)]
        ),
        "sweep": "ro_power",  # "index",#"current", # str. name of the sweep parameter
        # "ro_power":-15.55, # [dBm] ZInstrument output power
        "reset_delay": 5.1
        * T1,  # [sec] or False  (the same parameter in the higher nest will be used)
        "avg": 2
        ** 16,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
        "save_pulsesheet": True,
    },
    # Ramsey
    "ramsey": {
        "interval_sweep_start": 1e-10,
        "interval_sweep_stop": 80e-6,
        "interval_sweep_npts": 200,
        "sweep": "qu_freq_detune",  # "current", # str. name of the sweep parameter
        "reset_delay": 3
        * T2,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 12,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # T2 echo
    "echo": {
        "interval_sweep_start": 1e-10,
        "interval_sweep_stop": 40e-6,
        "interval_sweep_npts": 31,
        "logsweep": True,
        "interval_sweep_list": np.hstack(
            [np.linspace(0, T2, 11), logsweep(T2 * 1.1, 5 * T2, 11)]
        ),
        "sweep": False,  # "current", # str. name of the sweep parameter
        "reset_delay": 5.1
        * T1,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 13,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # interleaved T1 T2echo
    "interleaved": {
        # for T1
        "delay_sweep_list": np.hstack(
            [np.linspace(0, T1, 14), logsweep(T1 * 1.1, 5 * T1, 13)]
        ),
        # for T2 echo
        "interval_sweep_list": np.hstack(
            [np.linspace(0, T2, 14), logsweep(T2 * 1.1, 5 * T2, 13)]
        ),
        "index_num": 1000,
        "reset_delay": 5.1
        * T1,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 15,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed threetone
    "pulsed_threetone": {
        "ef_freq_step": 0.1e6,
        "ef_freq_start": qu_freq_12 - 5e6,
        "ef_freq_stop": qu_freq_12 + 5e6,
        "ef_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        # "ro_power":0,
        "ef_drive_power": -5,
        "ef_pulse_length": 252.4e-9,
        "reset_delay": 3
        * T1,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 13,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # dispersive shift
    "dispersive_shift": {
        "ro_freq_step": 0.2e6,  # [Hz]
        "ro_freq_start": ro_freq - 5e6,  # [Hz]
        "ro_freq_stop": ro_freq + 8e6,  # [Hz] must be larger than start
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "ro_pulse_length": 5e-6,  # [sec]
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 1000,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # ef-time rabi
    "ef_time_rabi": {
        "ef_pulse_length_step": False,
        "ef_pulse_length_start": 1e-10,
        "ef_pulse_length_stop": 300e-9,
        "ef_pulse_length_npts": 51,
        "sweep": False,  # "ef_freq", # str. name of the sweep parameter
        # "ef_pulse_length":42.4e-9,
        "ef_drive_power": -5,
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 2
        ** 12,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # Ramsey ef
    "ramsey_ef": {
        "interval_sweep_start": 1e-10,
        "interval_sweep_stop": 5e-6,
        "interval_sweep_npts": 50,
        "sweep": False,  # "qu_freq_detune",#"current", # str. name of the sweep parameter
        "reset_delay": 60e-6,  # 3*T2, #[sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 2,  # [#] or False (the same parameter in the higher nest will be used)
        "save_pulsesheet": True,
    },
    # Qubit temperature amp sweep
    "qu_temp_amp_sweep": {
        "ef_pulse_amp_step": False,
        "ef_pulse_amp_start": 0,
        "ef_pulse_amp_stop": 0.4387,  # 0.95,
        "ef_pulse_amp_npts": 2,
        "ef_pulse_length": 100e-9,
        "index_num": 1000,
        "ro_freq": ro_freq_e,
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 2
        ** 14,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # Raw onetone
    "RAW_onetone": {
        "sweep": False,
    },
    # Single shot measurement
    "single_shot": {
        "n_shots": 2**14,
        "sweep": "ro_power",
        # "ro_power":7, # [dBm] ZInstrument output power
        "ro_pulse_length": 18e-6,  # [sec]
        "reset_delay": 3 * T1,  # > 3*T1
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed_acStark_shift
    "pulsed_acStark_shift": {
        "qu_freq_step": 1e6,  # [Hz]
        "qu_freq_start": qu_freq + 50e6,  # [Hz]
        "qu_freq_stop": qu_freq - 50e6,  # [Hz] must be larger than start
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "cav_drive_power", # str. name of the sweep parameter
        "qu_power": -10,
        "qu_pi_pulse_length": 1e-6,  # [sec]
        "reset_delay": 50e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed_acStark_shift
    # "cav_drive_freq":None,
    "cav_drive_power": -10,
    "cav_drive_length": 1.5e-6,
    # "cav_drive_exLO_power":15,
    # "cav_drive_exLO_freq":None,
    "index": False,
    "qu_freq_detune": 0.1e6,  # [Hz] used only for ramsey measurement
    "pi_pulse_rep": 1,  # N pi pulses in T2 Echo measurement
    "readout_delay": 0e-9,  # time interval between pulse sequence and the readout
    "acquire_delay": 0e-9,
    "reset_delay": 3 * T1,  # [sec]
    "avg": 2**15,  # [#]
    "external_avg": 1,  # [#]
    "save_pulsesheet": True,
    # yokogawa setting
    # "gs_rampstep":1e-6,
    # "gs_delay":5000e-6,
    # "gs_voltage_lim": 5, # [V]
    # "gs_current_range": 10e-3,
    # sweep list
    "sweep_start": -5,
    "sweep_stop": 10,
    "sweep_npts": 7,
    "sweep_list": False,
    # "sweep_start":4.734e9-40e6,
    # "sweep_stop":4.734e9+40e6,
    # "sweep_npts":81,
    # "sweep_list":False,
}
# param_dict["cav_drive_freq"]=param_dict["qu_freq"]
# param_dict["cav_drive_exLO_freq"]=param_dict["ro_freq"]+param_dict["ro_exLO_freq"]-param_dict["cav_drive_freq"]
""" Note
"qu_freq_01": 4.7317e9,
"""
