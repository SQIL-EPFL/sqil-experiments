# -*- coding: utf-8 -*-
"""
Measurement code for CW one tone vs readout power
Equipment:
    Rohde&Schwarz ZNB port1 - port2

@author: taketo
"""

import matplotlib.pyplot as plt
import numpy as np
import qcodes as qc
import tqdm
from helpers.customized_drivers.Rohde_Schwarz_ZNA26 import RohdeSchwarzZNA26
from helpers.customized_drivers.ZNB_taketo import RohdeSchwarzZNBChannel
from helpers.taketo_datadict_storage import DataDict, DDH5Writer

######################################################################################################################
# data_path = r"Z:\Projects\RTmeasurement\20240920_bluefors_left_16"
# data_path = r"Z:\Projects\Transmon\Data\Sample10\RTmeasurment"
data_path = r"Z:\Projects\HighTempFluxonium\RT_Measurments\20241002_Alcavity_for_HTT"
exp_name = "farport"
tags = ["Alcavity", "farpin", "N18sacrified cavity"]

# power sweep
ro_power_list = np.linspace(0, 11, 1)

# NVA settings
ro_freqstep = 1e6
ro_freqstart = 19.1e9
ro_freqstop = 20.1e9
# ro_npts = 51
ro_npts = int((ro_freqstop - ro_freqstart) / ro_freqstep) + 1
ro_bw = 100  # bandwidth [Hz]
ro_avg = 1

frequency_list = np.linspace(ro_freqstart, ro_freqstop, ro_npts)

# connection with instruments
# vna = RohdeSchwarzZNB8('VNA', 'TCPIP0::128.178.120.232::inst0::INSTR', init_s_params=False)

# vna = RohdeSchwarzZNB8('VNA', 'TCPIP0::128.178.120.188::inst0::INSTR', init_s_params=False) # AQUA vna
vna = RohdeSchwarzZNA26(
    "VNA",
    r"TCPIP0::192.168.1.121::inst0::INSTR",
    init_s_params=False,
    reset_channels=False,
)
######################################################################################################################
###############S21##############################################################################
# # VNA
# chan = RohdeSchwarzZNBChannel(
#         vna,
#         name="S21",
#         channel=1,
#         vna_parameter="S21",
#         existing_trace_to_bind_to="Trc1",
#     )
# vna.channels.append(chan)
# vna.cont_meas_on()
# vna.display_single_window()
# vna.channels.S21.start(ro_freqstart)
# vna.channels.S21.stop(ro_freqstop)
# vna.channels.S21.npts(ro_npts)
# vna.channels.S21.bandwidth(ro_bw)
# vna.channels.S21.avg(ro_avg)
# vna.rf_on()
# station = qc.Station(vna)

# # define DataDict for saving in DDH5 format
# datadict = DataDict(
#         frequency=dict(unit="Hz"),
#         power=dict(unit="dBm"),
#         mag=dict(axes=["frequency", "power"], unit="dBm"),
#         phase=dict(axes=["frequency", "power"], unit="rad"),
#         )
# datadict.validate()

# with DDH5Writer(datadict, data_path, name=exp_name) as writer:
#     writer.add_tag(tags)
#     # writer.save_dict('param_dict.json',param_dict)
#     writer.backup_file([__file__])
#     writer.save_text("directry_path.md",f"{writer.filepath.parent}" )

#     # ro_power sweep
#     for ro_power in tqdm.tqdm(ro_power_list):
#         vna.channels.S21.power.set(ro_power)
#         mag, phase =vna.channels.S21.trace_db_phase.get()

#         writer.add_data(
#             frequency=frequency_list,
#             power=ro_power,
#             mag=mag,
#             phase=phase
#             )
#         plt.figure()
#         plt.plot(frequency_list*1e-9, mag)
#         plt.xlabel("Frequency [GHz]")
#         plt.ylabel("Magnitude [dB]")
#         plt.grid(visible=True, which="both", axis="both")
#         plt.savefig(f"{writer.filepath.parent}/ro_power_{ro_power}dBm.png", bbox_inches='tight')
# vna.rf_off()
# # vna.clear_channels()
# vna.close()

# #############S 12#############################################################################
# # VNA

# chan = RohdeSchwarzZNBChannel(
#         vna,
#         name="S12",
#         channel=1,
#         vna_parameter="S12",
#         existing_trace_to_bind_to="Trc1",
#     )
# vna.channels.append(chan)

# vna.cont_meas_on()
# vna.display_single_window()
# vna.channels.S12.start(ro_freqstart)
# vna.channels.S12.stop(ro_freqstop)
# vna.channels.S12.npts(ro_npts)
# vna.channels.S12.bandwidth(ro_bw)
# vna.channels.S12.avg(ro_avg)
# vna.rf_on()
# station = qc.Station(vna)

# # define DataDict for saving in DDH5 format
# datadict = DataDict(
#         frequency=dict(unit="Hz"),
#         power=dict(unit="dBm"),
#         mag=dict(axes=["frequency", "power"], unit="dBm"),
#         phase=dict(axes=["frequency", "power"], unit="rad"),
#         )
# datadict.validate()

# with DDH5Writer(datadict, data_path, name=exp_name) as writer:
#     writer.add_tag(tags)
#     # writer.save_dict('param_dict.json',param_dict)
#     writer.backup_file([__file__])

#     writer.save_text("directry_path.md",f"{writer.filepath.parent}" )

#     # ro_power sweep
#     for ro_power in tqdm.tqdm(ro_power_list):
#         vna.channels.S12.power.set(ro_power)
#         mag, phase = vna.channels.S12.trace_db_phase.get()

#         writer.add_data(
#             frequency=frequency_list,
#             power=ro_power,
#             mag=mag,
#             phase=phase
#             )
#         plt.figure()
#         plt.plot(frequency_list, mag)
#         plt.savefig(f"{writer.filepath.parent}/ro_power_{ro_power}dBm.png", bbox_inches='tight')
# vna.rf_off()
# # vna.clear_channels()
# vna.close()

# ###############S11##############################################################################
# VNA

chan = RohdeSchwarzZNBChannel(
    vna,
    name="S11",
    channel=1,
    vna_parameter="S11",
    existing_trace_to_bind_to="Trc1",
)
vna.channels.append(chan)

# vna.add_channel('S11')
vna.cont_meas_on()
vna.display_single_window()
vna.channels.S11.start(ro_freqstart)
vna.channels.S11.stop(ro_freqstop)
vna.channels.S11.npts(ro_npts)
vna.channels.S11.bandwidth(ro_bw)
vna.channels.S11.avg(ro_avg)
vna.rf_on()
station = qc.Station(vna)

# define DataDict for saving in DDH5 format
datadict = DataDict(
    frequency=dict(unit="Hz"),
    power=dict(unit="dBm"),
    mag=dict(axes=["frequency", "power"], unit="dBm"),
    phase=dict(axes=["frequency", "power"], unit="rad"),
)
datadict.validate()

with DDH5Writer(datadict, data_path, name=exp_name) as writer:
    writer.add_tag(tags)
    # writer.save_dict('param_dict.json',param_dict)
    writer.backup_file([__file__])
    writer.save_text("directry_path.md", f"{writer.filepath.parent}")

    # ro_power sweep
    for ro_power in tqdm.tqdm(ro_power_list):
        vna.channels.S11.power.set(ro_power)
        mag, phase = vna.channels.S11.trace_db_phase.get()

        writer.add_data(frequency=frequency_list, power=ro_power, mag=mag, phase=phase)
        plt.figure()
        plt.plot(frequency_list * 1e-9, mag)
        plt.xlabel("Frequency [GHz]")
        plt.ylabel("Magnitude [dB]")
        plt.savefig(
            f"{writer.filepath.parent}/ro_power_{ro_power}dBm.png", bbox_inches="tight"
        )
vna.rf_off()
# vna.clear_channels()
vna.close()

# ###############S22##############################################################################
# # VNA

# chan = RohdeSchwarzZNBChannel(
#         vna,
#         name="S22",
#         channel=1,
#         vna_parameter="S22",
#         existing_trace_to_bind_to="Trc1",
#     )
# vna.channels.append(chan)

# # vna.add_channel('S22')
# vna.cont_meas_on()
# vna.display_single_window()
# vna.channels.S22.start(ro_freqstart)
# vna.channels.S22.stop(ro_freqstop)
# vna.channels.S22.npts(ro_npts)
# vna.channels.S22.bandwidth(ro_bw)
# vna.channels.S22.avg(ro_avg)
# vna.rf_on()
# station = qc.Station(vna)

# # define DataDict for saving in DDH5 format
# datadict = DataDict(
#         frequency=dict(unit="Hz"),
#         power=dict(unit="dBm"),
#         mag=dict(axes=["frequency", "power"], unit="dBm"),
#         phase=dict(axes=["frequency", "power"], unit="rad"),
#         )
# datadict.validate()

# with DDH5Writer(datadict, data_path, name=exp_name) as writer:
#     writer.add_tag(tags)
#     # writer.save_dict('param_dict.json',param_dict)
#     writer.backup_file([__file__])
#     writer.save_text("directry_path.md",f"{writer.filepath.parent}" )

#     # ro_power sweep
#     for ro_power in tqdm.tqdm(ro_power_list):
#         vna.channels.S22.power.set(ro_power)
#         mag, phase =vna.channels.S22.trace_db_phase.get()

#         writer.add_data(
#             frequency=frequency_list,
#             power=ro_power,
#             mag=mag,
#             phase=phase
#             )
#         plt.figure()
#         plt.plot(frequency_list*1e-9, mag)
#         plt.xlabel("Frequency [GHz]")
#         plt.ylabel("Magnitude [dB]")
#         plt.savefig(f"{writer.filepath.parent}/ro_power_{ro_power}dBm.png", bbox_inches='tight')
# vna.rf_off()
# # vna.clear_channels()
# vna.close()
