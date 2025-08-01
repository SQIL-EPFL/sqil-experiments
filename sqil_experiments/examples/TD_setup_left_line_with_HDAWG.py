"""@author Taketo

Descriptor for the single qubit setup.
"""

from textwrap import dedent

descriptor_file = __file__

# database path
db_path = (
    r"Z:\Projects\Transmon\Data\Database\data\AQUA_leftline_double_transmon_240501"
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
    - address: dev12422
      uid: device_shfqc
  HDAWG:
    - address: dev9000
      uid: device_hdawg
  PQSC:
    - address: dev10190
      uid: device_pqsc

connections:
  device_shfqc:
  device_shfqc:
    - iq_signal: q0/measure
      ports: QACHANNELS/0/OUTPUT
    - acquire_signal: q0/acquire
      ports: QACHANNELS/0/INPUT

    - iq_signal: q0/shfqc_drive
      ports: SGCHANNELS/0/OUTPUT
    - iq_signal: q0/shfqc_drive_ef
      ports: SGCHANNELS/0/OUTPUT

  device_hdawg:
    - rf_signal: q0/hdawg_drive
      ports: SIGOUTS/0

  device_pqsc:
    - to: device_shfqc
      port: ZSYNCS/0
    - to: device_hdawg
      port: ZSYNCS/2
"""
)
