"""@author Taketo

Descriptor for the single qubit setup.
"""

from textwrap import dedent

descriptor_file = __file__

# database path
db_path = (
    r"Z:\Projects\Transmon\Data\Database\data\AQUA_rightline_transmon_240408\Tramsmon"
)

# wiring/RT attenuation setup
wiring = ""

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
    - address: dev12183
      uid: device_shfqc
  HDAWG:
    - address: dev8730
      uid: device_hdawg
  PQSC:
    - address: dev10195
      uid: device_pqsc
      
connections:
  device_shfqc:
    - iq_signal: q0/measure
      ports: QACHANNELS/0/OUTPUT
    - acquire_signal: q0/acquire
      ports: QACHANNELS/0/INPUT
    - iq_signal: q1/measure_line
      ports: QACHANNELS/0/OUTPUT
    - acquire_signal: q1/acquire_line
      ports: QACHANNELS/0/INPUT
      
    - iq_signal: q0/shfqc_drive
      ports: SGCHANNELS/2/OUTPUT
    - iq_signal: q0/shfqc_drive_ef
      ports: SGCHANNELS/2/OUTPUT
      
  device_hdawg:
    - rf_signal: q0/flux_line
      ports: SIGOUTS/2
      
  device_pqsc:
    - to: device_shfqc
      port: ZSYNCS/0
    - to: device_hdawg
      port: ZSYNCS/1
"""
)
