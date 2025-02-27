import numpy as np

pd_file = __file__


ro_freq = 20.897e9  # [Hz]
qu_freq = 6.481e9  # [Hz]
qu_freq02_by2 = 6.346e9
freq_03 = 18.6086e9
# freq_05 = 24.5e9

# two_chi = 10e6 #[Hz]

param_dict = {
    "ro_freq": ro_freq,
    "ro_power": -30,  # [dBm]
    "qu_freq": qu_freq,
    "qu_power": 10,  # [dBm]
    "current": 0e-3,  # [A]
    #### CW onetone ####
    "CW_onetone": {
        "ro_freq_step": 0.1e6,  # [Hz]
        "ro_freq_start": ro_freq - 200e6,  # [Hz]
        "ro_freq_stop": ro_freq + 200e6,  # [Hz] must be larger than start
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "ro_power", # str. name of the sweep parameter
    },
    #### CW twotone ####
    "CW_twotone": {
        "qu_freq_step": 2e6,  # 0.05e6, # [Hz]
        "qu_freq_start": 28e9,  # [Hz]
        "qu_freq_stop": 30e9,  # qu_freq+300e6, # [Hz]
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # str. name of the sweep parameter
    },
    #### CW twotone sweep readout frequency ####
    "CW_twotone_sweep_ro_freq": {
        "ro_freq_step": 0.5e6,  # [Hz]
        "ro_freq_start": ro_freq - 200e6,  # [Hz]
        "ro_freq_stop": ro_freq + 200e6,  # [Hz] must be larger than start
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # str. name of the sweep parameter
    },
    #### VNA setting ####
    "vna_bw": 5,  # bandwidth [Hz]
    "vna_avg": 1,  # 10# average [#]
    #### yokogawa setting ####
    # "gs_rampstep":1e-6,
    # "gs_delay":5000e-6,
    # "gs_voltage_lim": 5, # [V]
    # "gs_current_range": 10e-3,
    "index": False,
    #### sweep list ####
    #### sweep list ####
    # "sweep_start":20.35e9-6*two_chi,
    # "sweep_stop":20.35e9+6*two_chi,
    # "sweep_npts":41,
    # "sweep_list":False, #s[10*np.log10(p_mW) for p_mW in np.linspace(0.016, 0.027, 5)]
    "sweep_start": -40,
    "sweep_stop": 15,  # -40
    "sweep_npts": 111,  # 10
    "sweep_list": False,  # [10*np.log10(p_mW) for p_mW in np.linspace(0.001, 0.002, 10)],
}
""" Note
"qu_freq_01": 4.7317e9,
"""
