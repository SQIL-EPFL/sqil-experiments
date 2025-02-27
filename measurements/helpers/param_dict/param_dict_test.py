pd_file = __file__

param_dict = {
    "ro_freq": 19e9,
    "ro_power": -30,  # [dBm]
    "qu_freq_01": None,
    "qu_power": -30,
    "current": 0,  # [A]
    # CW onetone
    "CW_onetone": {
        "ro_freq_step": 2e6,  # [Hz]
        "ro_freq_start": 10e9,  # [Hz]
        "ro_freq_stop": 26.5e9,  # [Hz]
        "ro_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "qu_power": -10,  # [dBm]
        "sweep": False,  # str. name of the sweep parameter
    },
    # CW twotone
    "CW_twotone": {
        "qu_freq_step": 1e6,  # [Hz]
        "qu_freq_start": 10e9,  # [Hz]
        "qu_freq_stop": 20e9,  # [Hz]
        "qu_freq_npts": False,  # if "False", npts is calculated using ro_freqstep
        "sweep": False,  # str. name of the sweep parameter
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
    "vna_bw": 1e3,  # bandwidth [Hz]
    "vna_avg": 1,  # average [#]
    # yokogawa setting
    "gs_rampstep": 1e-6,
    "gs_delay": 500e-6,
    "gs_voltage_lim": 5,  # [V]
    "gs_current_range": 10000e-6,
    # sweep list
    "sweep_start": False,
    "sweep_stop": False,
    "sweep_npts": False,
}

""" Note

"""
