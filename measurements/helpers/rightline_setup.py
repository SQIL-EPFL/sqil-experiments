from laboneq.simple import DeviceSetup, SHFQC, create_connection

def get_device_setup() -> DeviceSetup:
    setup = DeviceSetup("fridge_rightline")
    setup.add_dataserver(host="localhost", port=8004)

    setup.add_instruments(
        SHFQC(uid="device_shfqc", address="dev12183", device_options="SHFQC/QC6CH"),
    )

    setup.add_connections("device_shfqc",
        create_connection(to_signal="q0/measure", ports="QACHANNELS/0/OUTPUT"),
        create_connection(to_signal="q0/acquire", ports="QACHANNELS/0/INPUT"),
        create_connection(to_signal="q0/shfqc_drive", ports="SGCHANNELS/0/OUTPUT"),
        create_connection(to_signal="q0/shfqc_drive_ef", ports="SGCHANNELS/0/OUTPUT"),
    )

    return setup
