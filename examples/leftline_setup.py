from laboneq.simple import HDAWG, PQSC, SHFQC, DeviceSetup, create_connection


def get_device_setup() -> DeviceSetup:
    setup = DeviceSetup("fridge_leftline")
    setup.add_dataserver(host="localhost", port=8004)

    setup.add_instruments(
        SHFQC(uid="device_shfqc", address="dev12422", device_options="SHFQC/QC6CH"),
        HDAWG(
            uid="device_hdawg", address="dev9000", device_options="HDAWG8/MF/ME/SKW/PC"
        ),
        PQSC(uid="device_pqsc", address="dev10190"),
    )

    setup.add_connections(
        "device_shfqc",
        create_connection(to_signal="q0/measure", ports="QACHANNELS/0/OUTPUT"),
        create_connection(to_signal="q0/acquire", ports="QACHANNELS/0/INPUT"),
        create_connection(to_signal="q0/shfqc_drive", ports="SGCHANNELS/0/OUTPUT"),
        create_connection(to_signal="q0/shfqc_drive_ef", ports="SGCHANNELS/0/OUTPUT"),
    )

    setup.add_connections(
        "device_hdawg",
        create_connection(to_signal="q0/flux_line", ports="SIGOUTS/0"),
    )

    setup.add_connections(
        "device_pqsc",
        create_connection(to_instrument="device_shfqc", ports="ZSYNCS/0"),
        create_connection(to_instrument="device_hdawg", ports="ZSYNCS/2"),
    )

    return setup
