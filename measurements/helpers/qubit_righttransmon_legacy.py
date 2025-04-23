from laboneq.contrib.example_helpers.barebones.tunable_transmon import TunableTransmon

class ExperimentSettings:
    def __init__(self, avg=2**12, external_avg=1, save_pulsesheet=True, plot_fit=True):
        self.external_avg = external_avg
        self.save_pulsesheet = save_pulsesheet
        self.plot_fit = plot_fit
        self.avg = avg

def create_qubit_from_param_dict(param_dict: dict) -> tuple[TunableTransmon, ExperimentSettings]:

    def get(key, default):
        return param_dict.get(key, default)

    qubit = TunableTransmon(
        name="q0",
        readout_amplitude=1.0,
        drive_amplitude=1.0,
        port_delay=0,
    )

    # Ajout de tous les attributs dynamiquement en respectant les noms exacts du param_dict
    qubit.ro_freq = get("ro_freq", 7557906800)
    qubit.ro_lo_freq = get("ro_lo_freq", 7.3e9)
    qubit.ro_power = get("ro_power", -30)
    qubit.ro_acquire_range = get("ro_acquire_range", -5)
    qubit.ro_pulse_length = get("ro_pulse_length", 3e-6)
    qubit.qu_freq_start = get("qu_freq_start", 6.215e9)
    qubit.qu_freq_stop = get("qu_freq_stop", 6.225e9)
    qubit.qu_freq_npts = get("qu_freq_npts", 501)
    qubit.qu_lo_freq = get("qu_lo_freq", 5.9e9)
    qubit.qu_drive_power = get("qu_drive_power", -20)
    qubit.qu_drive_pwm_freq = get("qu_drive_pwm_freq", 0e6)
    qubit.qu_pulse_length = get("qu_pulse_length", 2000e-9)
    qubit.reset_delay = get("reset_delay", 1e-6)

    settings = ExperimentSettings(
    external_avg=get("external_avg", 1),
    save_pulsesheet=get("save_pulsesheet", True),
    plot_fit=get("plot_fit", True),
    avg=get("avg", 2**14)
)

    return qubit, settings
