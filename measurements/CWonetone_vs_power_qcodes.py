# -*- coding: utf-8 -*-
"""
This code is a test code for plottr-monitr
Measurement code for CW one tone vs readout power
Equipment:
    Rohde&Schwarz ZNB port1 - port2

@author: taketo
"""

import datetime

import numpy as np
import qcodes as qc
import tqdm
from helpers.customized_drivers.Rohde_Schwarz_ZNA26 import RohdeSchwarzZNA26

# from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from qcodes.dataset import (
    Measurement,
    extract_runs_into_db,
    initialise_or_create_database_at,
    load_or_create_experiment,
)
from qcodes.instrument_drivers.rohde_schwarz import (
    RohdeSchwarzZNB8,
    RohdeSchwarzZNBChannel,
)

######################################################################################################################
data_path = r"Z:\Projects\HighTempFluxonium\Samples\HTF4\data\20240824"
# db_name = r"\hightempfluxonium4.db"
# server_db_path = r"Z:\Projects\HighTempFluxonium\QCoDeSdatabase"
exp_name = "onetone_vs_power"
sample_name = "HTFin19GHz"

# power sweep
ro_power_list = np.linspace(-40, 0, 11)

# NVA settings
ro_freqstep = 2e6
ro_freqstart = 19e9
ro_freqstop = 20e9
ro_npts = int((ro_freqstop - ro_freqstart) / ro_freqstep) + 1
ro_bw = 500  # bandwidth [Hz]
ro_avg = 1

# connection with instruments
vna = RohdeSchwarzZNA26(
    "VNA", r"TCPIP0::192.168.1.121::inst0::INSTR", init_s_params=False
)
######################################################################################################################

# VNA
vna.add_channel("S21")
vna.cont_meas_on()
vna.display_single_window()
vna.channels.S21.start(ro_freqstart)
vna.channels.S21.stop(ro_freqstop)
vna.channels.S21.npts(ro_npts)
vna.channels.S21.bandwidth(ro_bw)
vna.channels.S21.avg(ro_avg)

# db_fullpath = db_path + db_name
# initialise_or_create_database_at(db_fullpath)
# load_or_create_experiment(experiment_name=exp_name,
#                           sample_name=sample_name)
station = qc.Station(vna)

data = DataDict(
    frequency=dict(unit="Hz"),
    power=dict(unit="dBm"),
    s21_mag=dict(axes=["frequency", "power"], unit="dBm"),
    s21_phase=dict(axes=["frequency", "power"], unit="rad"),
)
data.validate()

tags = ["CW", "test"]

with DDH5Writer(data, data_path, name=exp_name) as writer:
    writer.add_tag(tags)
    # writer.backup_file([__file__, setup_file])
    # writer.save_text("wiring.md", wiring)
    writer.save_dict("station_snapshot.json", station.snapshot())
    vna.rf_on()
    for ro_power in tqdm.tqdm(ro_power_list):
        vna.channels.S21.power.set(ro_power)
        mag, phase = vna.channels.S21.trace_db_phase.get()
        writer.add_data(
            frequency=np.linspace(ro_freqstart, ro_freqstop, ro_npts),
            power=ro_power,
            s21_mag=mag,
            s21_phase=phase,
        )

# meas = Measurement()
# meas.register_parameter(vna.channels.S21.power)
# meas.register_parameter(vna.channels.S21.trace_db_phase, setpoints=(vna.channels.S21.power,))
# vna.rf_on()
# with meas.run() as datasaver:
#     for ro_power in tqdm.tqdm(ro_power_list):
#         vna.channels.S21.power.set(ro_power)
#         get_v =vna.channels.S21.trace_db_phase.get()
#         datasaver.add_result((vna.channels.S21.power, ro_power),
#                                  (vna.channels.S21.trace_db_phase, get_v))
vna.rf_off()
vna.clear_channels()
vna.close()
