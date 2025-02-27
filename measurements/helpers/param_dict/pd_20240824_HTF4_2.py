pd_file = __file__

param_dict = {
    "ro_freq": 19.63e9,  # [Hz]
    "ro_power": -42,  # [dBm]
    "qu_freq_01": None,
    "qu_power": 0,
    "current": -0.995e-3,  # [A]
    # CW onetone
    "CW_onetone": {
        "ro_freq_step": 1e6,  # [Hz]
        "ro_freq_start": 19.627e9 - 50e6,  # [Hz]
        "ro_freq_stop": 19.627e9 + 50e6,  # [Hz]
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # str. name of the sweep parameter
    },
    # CW twotone
    "CW_twotone": {
        "qu_freq_step": 1e6,  # [Hz]
        "qu_freq_start": 14e9,  # [Hz]
        "qu_freq_stop": 18e9,  # [Hz]
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "current", # str. name of the sweep parameter
    },
    # # CW pulsed-twotone
    # "CW_pulsed_twotone":{
    #     "qu_pulse_length":2e-6, # [sec]
    #     "qu_freq_step":1e6, # [Hz]
    #     "qu_freq_start":10e9, # [Hz]
    #     "qu_freq_stop":20e9, # [Hz]
    #     "qu_freq_npts":False, # if "False", npts is calculated using ro_freqstep
    #     "sweep":False, # str. name of the sweep parameter
    # },
    # VNA setting
    "vna_bw": 5,  # 2,#1, # bandwidth [Hz]
    "vna_avg": 5,  # 8, # average [#]
    # yokogawa setting
    "gs_rampstep": 1e-6,
    "gs_delay": 5000e-6,
    "gs_voltage_lim": 5,  # [V]
    "gs_current_range": 10e-3,
    # sweep list
    "sweep_start": -1.58e-3 - 0.1e-3,
    "sweep_stop": -0.995e-3 + 0.1e-3,
    "sweep_npts": 41,
    # "sweep_start":-2.0e-3,
    # "sweep_stop":1.0e-3,
    # "sweep_npts":301,
    # "sweep_start":-54,
    # "sweep_stop":-40,
    # "sweep_npts":8,
}

""" Note

"""
