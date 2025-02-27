import sys

import numpy as np

sys.path.append(r"Z:\Projects\HighTempFluxonium\Measurement\measurement_codes\helpers")
from utilities import logsweep

pd_file = __file__


ro_freq = 3.08e9  # [Hz]
ro_freq_e = 3.068e9  # [Hz] # measuring |e> state
# qu_freq = 4.67444e9 #[Hz]
qu_freq = 4.67528e9  # At 140 mK
qu_freq_12 = 4.4236e9
gf_by2_freq = 4.604e9  # [Hz]
freq_03 = 13.40e9

# qu_freq = 4.72985e9 #[Hz]
gf_by2_freq = 4.604e9  # [Hz]

two_chi = 13.6e6  # [Hz]

pi_pulse = 35e-9
qu_power = 9.55

# pi_pulse=70e-9
# qu_power=4.4

# pi_pulse=140e-9
# qu_power=-1.15

# pi_pulse=280e-9
# qu_power=-7

# pi_pulse=560e-9
# qu_power=-13.18


# T1=46e-6
# T2=38e-6
# T=58mK
# T1=46e-6
# T2=35e-6
# T=95mK
# T1=38e-6
# T2=28e-6
# T=120mK
# T1=42e-6
# T2=20e-6
# T=140mK
T1 = 32e-6
T2 = 11e-6

param_dict = {
    "ro_freq": ro_freq,  # [Hz] SHFQC output frequenc2.6
    "ro_lo_freq": 2.6e9,  # ro_if_freq = ro_freq-ro_lo_freq
    "ro_pulse_length": 2e-6,  # [sec]
    "ro_power": 3,  # [dBm] ZInstrument output power
    "ro_acquire_range": -30,
    # external LO source (Signal core)
    "ro_exLO_freq": 17.312e9,  # 17.392e9-0.0e9, # This freq cannot be detuned by more than 500MHz from "ro_freq"
    "ro_exLO_power": 15,  # [dBm]
    "qu_freq": qu_freq,
    "qu_lo_freq": 4.4e9,  # [GHz]
    "qu_pi_pulse_length": pi_pulse,
    "qu_power": qu_power,
    "ef_freq": qu_freq_12,
    "ef_pulse_length": 20e-9,
    # "ef_lo_freq":5.6e9, # cannot use different lo freq for the same output line!
    "ef_drive_power": 9.55,  # maybe need to be lower than "qu_power"(second tone). need to be fixed.
    "current": 0e-3,  # [A]
    # pulsed onetone
    "pulsed_onetone": {
        "ro_freq_step": 1e6,  # [Hz]
        "ro_freq_start": ro_freq - 50e6,  # [Hz]
        "ro_freq_stop": ro_freq + 50e6,  # [Hz] must be larger than start
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "ro_exLO_freq",#"current", # str. name of the sweep parameter
        "ro_pulse_length": 10e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "reset_delay": 0.1e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 1000,  # 10000, # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed twotone
    "pulsed_twotone": {
        "qu_freq_step": 0.1e6,  # [Hz]
        "qu_freq_start": qu_freq + 7e6,  # [Hz]
        "qu_freq_stop": qu_freq - 7e6,  # [Hz] must be larger than start
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "qu_power": -35,
        "qu_pulse_length": 2000e-9,  # [sec]
        "reset_delay": 0.1e-6,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # time rabi
    "time_rabi": {
        "qu_pulse_length_step": False,
        "qu_pulse_length_start": 1e-10,
        "qu_pulse_length_stop": 10e-6,  # 80e-9,
        "qu_pulse_length_npts": 280,
        "sweep": "qu_freq",  # False,#"current", # str. name of the sweep parameter
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 2
        ** 15,  # [#] or False (the same parameter in the higher nest will be used)
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
        ** 15,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # T1
    "T1": {
        "delay_sweep_start": 1e-10,
        "delay_sweep_stop": 3 * T1,
        "delay_sweep_npts": 100,
        "logsweep": False,
        "delay_sweep_list": np.hstack(
            [np.linspace(0, T1, 11), logsweep(T1 * 1.1, 5 * T1, 11)]
        ),
        "sweep": False,  # "current", # str. name of the sweep parameter
        "ro_freq": ro_freq_e,
        "reset_delay": 3
        * T1,  # [sec] or False  (the same parameter in the higher nest will be used)
        "avg": 2
        ** 15,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # Ramsey
    "ramsey": {
        "interval_sweep_start": 1e-10,
        "interval_sweep_stop": 10e-6,
        "interval_sweep_npts": 100,
        "sweep": False,  # "qu_freq_detune",#"current", # str. name of the sweep parameter
        "reset_delay": 3
        * T2,  # [sec] or False (the same parameter in the higher nest will be used)
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
            [np.linspace(0, T2, 11), logsweep(T2 * 1.1, 5 * T2, 11)]
        ),
        "sweep": False,  # "current", # str. name of the sweep parameter
        "reset_delay": 3.3
        * T1,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 15,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # interleaved T1 T2echo
    "interleaved": {
        # for T1
        "delay_sweep_list": np.hstack(
            [np.linspace(0, T1, 11), logsweep(T1 * 1.1, 5 * T1, 11)]
        ),
        # for T2 echo
        "interval_sweep_list": np.hstack(
            [np.linspace(0, T2, 11), logsweep(T2 * 1.1, 5 * T2, 11)]
        ),
        "index_num": 1000,
        "reset_delay": 3.3
        * T1,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 16,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # pulsed threetone
    "pulsed_threetone": {
        "ef_freq_step": 0.1e6,
        "ef_freq_start": qu_freq_12 - 5e6,
        "ef_freq_stop": qu_freq_12 + 5e6,
        "ef_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
        "ef_pulse_length": 10e-6,
        "reset_delay": 3
        * T1,  # [sec] or False (the same parameter in the higher nest will be used)
        "avg": 2
        ** 15,  # [#] or False (the same parameter in the higher nest will be used)
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
        ** 13,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 1,  # [#] or False (the same parameter in the higher nest will be used)
    },
    # ef-time rabi
    "ef_time_rabi": {
        "ef_pulse_length_step": False,
        "ef_pulse_length_start": 1e-10,
        "ef_pulse_length_stop": 60e-9,
        "ef_pulse_length_npts": 31,
        "sweep": False,  # "current", # str. name of the sweep parameter
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
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
        "ef_pulse_amp_stop": 0.248,  # 0.95,
        "ef_pulse_amp_npts": 2,
        "ef_pulse_length": 100e-9,
        "index_num": 100,
        "ro_freq": ro_freq_e,
        "reset_delay": 3 * T1,  # > 3*T1
        "avg": 2
        ** 17,  # [#] or False (the same parameter in the higher nest will be used)
        "external_avg": 2,  # [#] or False (the same parameter in the higher nest will be used)
    },
    "index": False,
    "qu_freq_detune": 0.8e6,  # [Hz] used only for ramsey measurement
    "pi_pulse_rep": 1,  # N pi pulses in T2 Echo measurement
    "readout_delay": 0e-9,  # time interval between pulse sequence and the readout
    "acquire_delay": 0e-9,
    "reset_delay": 100e-6,  # [sec]
    "avg": 2**15,  # [#]
    "external_avg": 1,  # [#]
    "save_pulsesheet": False,
    # yokogawa setting
    # "gs_rampstep":1e-6,
    # "gs_delay":5000e-6,
    # "gs_voltage_lim": 5, # [V]
    # "gs_current_range": 10e-3,
    # sweep list
    "sweep_start": qu_freq + 0.4e6,
    "sweep_stop": qu_freq - 0.8e6,
    "sweep_npts": 40,
    "sweep_list": False,
    # "sweep_start":4.734e9-40e6,
    # "sweep_stop":4.734e9+40e6,
    # "sweep_npts":81,
    # "sweep_list":False,
}
""" Note
"qu_freq_01": 4.7317e9,
"""
