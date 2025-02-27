pd_file = __file__

param_dict = {
    "ro_freq": 19.632e9,  # [Hz]
    "ro_power": 10,  # [dBm]
    "qu_freq_01": None,
    "qu_power": -1.66,
    "current": 0e-3,  # [A]
    # CW onetone
    "CW_onetone": {
        "ro_freq_step": 10e6,  # [Hz]
        "ro_freq_start": 2.0e9,  # [Hz]
        "ro_freq_stop": 20e9,  # [Hz] must be larger than start
        "ro_freq_npts": 1,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # "ro_power",#"current", # str. name of the sweep parameter
    },
    # CW twotone
    "CW_twotone": {
        "qu_freq_step": 2e6,  # [Hz]
        "qu_freq_start": 19.75e9,  # [Hz]
        "qu_freq_stop": 23e9,  # [Hz]
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": "current",  # str. name of the sweep parameter
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
    "vna_bw": 1,  # 2,#1, # bandwidth [Hz]
    "vna_avg": 1,  # 8, # average [#]
    # yokogawa setting
    "gs_rampstep": 1e-6,
    "gs_delay": 5000e-6,
    "gs_voltage_lim": 5,  # [V]
    "gs_current_range": 10e-3,
    # sweep list
    # "sweep_start":-1.58e-3-0.1e-3,
    # "sweep_stop":-0.995e-3+0.1e-3,
    # "sweep_npts":61,
    # "sweep_start":-1.58e-3-0.1e-3,
    # "sweep_stop":-0.995e-3+0.1e-3,
    # "sweep_npts":51,
    # "sweep_start":19.62e9,
    # "sweep_stop":19.65e9,
    # "sweep_npts":31,
    "sweep_start": -60,
    "sweep_stop": 10,
    "sweep_npts": 15,
}

""" Note
sweetspot (HFQ?):-1.58e-3 f_r 19.635e9
sweetspot (IFQ?): -0.995e-3
"""
