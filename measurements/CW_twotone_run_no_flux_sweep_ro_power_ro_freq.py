"""
for fluxonium measurement.
CW twotone with VNA and Signal Core.
@Taketo
"""

import datetime
import json
import os
import sys
import time
from distutils.dir_util import copy_tree

import h5py
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from helpers.customized_drivers.Rohde_Schwarz_ZNA26 import RohdeSchwarzZNA26
from helpers.customized_drivers.ZNB_taketo import RohdeSchwarzZNBChannel
from helpers.setup.CW_Setup import (  # yoko_IP,
    db_path,
    db_path_local,
    param_dict,
    pd_file,
    setup_file,
    sgs_IP,
    vna_IP,
    wiring,
)
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from helpers.utilities import current_range_check

# from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A
from qcodes.instrument_drivers.rohde_schwarz import RohdeSchwarzSGS100A

sys.path.append("../analysis_code")
from CW_twotone_plot import *
from spectroscopy_1D_plot import spectroscopy_1D_plot
from spectroscopy_2D_plot import spectroscopy_2D_plot

sweep_dict = {
    -25.0: 20.3465e9,  # 0
    -24.0: 20.3465e9,  # 1
    -23.0: 20.3455e9,  # 2
    -22.0: 20.346e9,  # 3
    -21.0: 20.346e9,
    -20.0: 20.347e9,
    -19.0: 20.3465e9,
    -18.0: 20.3445e9,
    -17.0: 20.3455e9,
    -16.0: 20.344e9,
    -15.0: 20.3335e9,  # 10
    -14.0: 20.3345e9,
    -13.0: 20.3425e9,
    -12.0: 20.329e9,  # 13
    -11.0: 20.327e9,  # 14
    -10.0: 20.325e9,
    -9.0: 20.324e9,  # 16
    -8.0: 20.324e9,  # 17
    -7.0: 20.3205e9,
    -6.0: 20.3215e9,
    -5.0: 20.3175e9,  # 20
    -4.0: 20.318e9,  # 21
    -3.0: 20.3185e9,
    -2.0: 20.317e9,
    -1.0: 20.3165e9,
    0.0: 20.316e9,
    1.0: 20.3155e9,
    2.0: 20.313e9,
    3.0: 20.3115e9,
    4.0: 20.31e9,
    5.0: 20.2955e9,
    # 6.0: 20.2855e9,
    # 7.0: 20.283e9,
    # 8.0: 20.2925e9,
    # 9.0: 20.294e9,
    # 10.0: 20.296e9,
}

exp_name = "CW_twotone_sweep_ro_power_ro_freq"
tags = ["0_CW twotone"]

# define qubit drive frequency list
freq_start = param_dict["CW_twotone"]["qu_freq_start"]
freq_stop = param_dict["CW_twotone"]["qu_freq_stop"]
if param_dict["CW_twotone"]["qu_freq_npts"] == False:
    freq_npts = (
        int(abs(freq_stop - freq_start) / param_dict["CW_twotone"]["qu_freq_step"]) + 1
    )
else:
    freq_npts = param_dict["CW_twotone"]["qu_freq_npts"]
param_dict["CW_twotone"]["qu_freq_npts"] = freq_npts  # update freq_npts to param_dict
freq_list = np.linspace(freq_start, freq_stop, freq_npts)

# define datadict
tags.append(f"0_{exp_name}")
param_dict[param_dict["CW_twotone"]["sweep"]] = "sweeping"
# define DataDict for saving in DDH5 format
datadict = DataDict(
    qu_freq=dict(unit="sec"),
    ro_power=dict(unit=""),
    mag_dB=dict(axes=["qu_freq", "ro_power"], unit="dB"),
    phase=dict(axes=["qu_freq", "ro_power"], unit="rad"),
)
datadict.validate()

with DDH5Writer(datadict, db_path_local, name=exp_name) as writer:
    filepath_parent = writer.filepath.parent
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, pd_file])
    writer.save_text("wiring.md", wiring)

    # take the last two stages of the filepath_parent
    path = str(filepath_parent)
    last_two_parts = path.split(os.sep)[-2:]
    new_path = os.path.join(db_path, *last_two_parts)
    writer.save_text("directry_path.md", new_path)

    # connect to the equipment
    vna = RohdeSchwarzZNA26(
        "VNA",
        vna_IP,
        init_s_params=False,
        reset_channels=False,
    )
    # sc = SC5521A('mw1')

    sgsa = RohdeSchwarzSGS100A("SGSA100", sgs_IP)

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
    # vna.cont_meas_on()
    # vna.display_single_window()
    # vna.channels.S21.sweep_type('CW_Point')
    # vna.channels.S21.power.set(-50) # for safety

    # vna.add_channel('S21')
    vna.cont_meas_on()
    vna.display_single_window()
    vna.channels.S21.power.set(-50)  # for safety

    # setting of signal core
    # sc.power(-10) # for safety
    # sc.status("off")
    # sc.clock_frequency(10)

    # setting of R&S SGS100A
    sgsa.status(False)
    sgsa.power(-60)  # for safety

    vna.rf_on()
    # sc.status('on')
    sgsa.status(True)
    for ro_power, ro_freq in tqdm.tqdm(sweep_dict.items()):

        ## update parameters
        # setting of VNA
        vna.channels.S21.npts(1)
        vna.channels.S21.start(ro_freq)
        vna.channels.S21.stop(ro_freq)
        vna.channels.S21.power.set(ro_power)
        vna.channels.S21.bandwidth(param_dict["vna_bw"])
        vna.channels.S21.avg(param_dict["vna_avg"])

        # setting of Signal Core
        # sc.power(param_dict["qu_power"])
        sgsa.power(param_dict["qu_power"])

        mag_dB_array = np.zeros(freq_npts)
        phase_array = np.zeros(freq_npts)
        # measurement
        for idx, qu_freq in enumerate(freq_list):
            # sc.frequency(qu_freq)
            sgsa.frequency(qu_freq)
            # time.sleep(0.25)
            # vna.channels.S21.autoscale()
            # mag_dB, phase =vna.channels.S21.point_fixed_frequency_db_phase.get()
            # mag_dB, phase =vna.channels.S21.point_fixed_frequency_mag_phase.get()
            mag_dB, phase = vna.channels.S21.trace_db_phase.get()
            mag_dB_array[idx] = mag_dB[0]
            phase_array[idx] = phase[0]

            # # record the measurement time (in YYYYMMDDhhmmss format)
            # now = datetime.datetime.now()
            # time = int(now.strftime('%Y%m%d%H%M%S'))

            writer.add_data(
                qu_freq=qu_freq, ro_power=ro_power, mag_dB=mag_dB, phase=phase
            )

    vna.rf_off()
    # sc.status('off')
    sgsa.status(False)
    vna.close()
    # sc.close()
    sgsa.close()

### plotting
path = str(filepath_parent)
print(path)


# copy the directory to the server
copy_tree(filepath_parent, new_path)
