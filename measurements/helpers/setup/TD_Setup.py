"""@author Taketo
Set up file for fluxonium CW measurement.
"""

import sys
from textwrap import dedent

setup_file = __file__

# database path
# db_path_local=r"C:\Users\sqil\Desktop\data_local\HighTempFluxonium\HTT_a_N5\20250212_TD_line1"
# db_path=r"Z:\Projects\HighTempFluxonium\Samples\HTT_a_N5\data\20250212_TD_line1"
# database path
db_path_local = (
    r"C:\Users\sqil\Desktop\data_local\HighTempFluxonium\HTT_b_N20\20250212_TD_line2"
)
db_path = r"Z:\Projects\HighTempFluxonium\Samples\HTT_b_N20\data\20250212_TD_line2"

# import param_dict
sys.path.append(
    r"Z:\Projects\HighTempFluxonium\Measurement\measurement_codes\helpers\param_dict"
)
# from pd_20250212_HTT_a_N5_TD_line1 import pd_file, param_dict
from pd_20250212_HTT_b_N20_TD_line2 import param_dict, pd_file

# from pd_20250212_HTT_b_N20_TD_line2_withSGS import pd_file, param_dict


# wiring/RT attenuation setup
wiring = "\n".join(
    [
        "SHFQA_readout - 3feet(T40-3FT-KMKM+) - RT amp(MiniCircuits/ZX60-83LN-S+) - SMAmale-male - ",
        # "R&S_SGS100A - 2feet(T40-2FT-KMKM+) - 10dB - 10dB - PowerSplitter(ZN4PD-K44+)_port2",
        # "PowerSplitter(ZN4PD-K44+)_portS - 6dB - 6feet(E40-6FT-KMKM+) - In11",
        # "Out - RTamp - 6feet(E40-6FT-KMKM+) - SMAfemale-female - 2feet(T40-2FT-KMKM+) - ZNA26_port2",
    ]
)

# Instrument IP address
vna_IP = r"TCPIP0::192.168.1.200::inst0::INSTR"  # AQUA ZNA26.5GHz
# vna_IP = r'TCPIP0::192.168.1.131::inst0::INSTR' # SQIL ZNB20.0GHz
yoko_IP = r"TCPIP0::192.168.1.60::inst0::INSTR"
sgs_IP = r"TCPIP0::192.168.1.17::inst0::INSTR"

# ZI descriptor
main_descriptor = dedent(
    """\
dataservers:
  my_qccs_system:
    host: localhost
    port: 8004
    instruments: [device_shfqc, device_hdawg, device_pqsc]
            
instruments:
  SHFQC:
    - address: dev12551
      uid: device_shfqc
  HDAWG:
    - address: dev9131
      uid: device_hdawg
  PQSC:
    - address: dev10219
      uid: device_pqsc
      
connections:
  device_shfqc:
    - iq_signal: q0/measure
      ports: QACHANNELS/0/OUTPUT
    - acquire_signal: q0/acquire
      ports: QACHANNELS/0/INPUT
    # cavity drive  
    - iq_signal: q0/cav_drive_measure
      ports: QACHANNELS/0/OUTPUT
    - acquire_signal: q0/cav_drive_acquire
      ports: QACHANNELS/0/INPUT
      
    - iq_signal: q0/shfqc_drive
      ports: SGCHANNELS/0/OUTPUT
    - iq_signal: q0/shfqc_drive_ef
      ports: SGCHANNELS/0/OUTPUT
    - iq_signal: q0/shfqc_drive_cav
      ports: SGCHANNELS/1/OUTPUT
    # - external_clock_signal
      
  device_hdawg:
    - rf_signal: q0/hdawg_drive
      ports: SIGOUTS/0
      
  device_pqsc:
    - to: device_shfqc
      port: ZSYNCS/0
    - to: device_hdawg
      port: ZSYNCS/1
"""
)
