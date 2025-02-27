import numpy as np
from helpers.utilities import shfqa_power_calculator
from laboneq.simple import *

exp_file = __file__


def main_exp(session, param_dict):
    # create exp object and define the ExperimentSignal lines
    exp = Experiment(
        uid="exp",
        signals=[
            ExperimentSignal("measure"),
            ExperimentSignal("acquire"),
            ExperimentSignal("qu_drive"),
        ],
    )

    # define the signal mapping between the LogicalSignals and the ExperimentSignals
    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        "qu_drive": "/logical_signal_groups/q0/shfqc_drive",
    }
    exp.set_signal_map(signal_map)

    # define an experiment calibration (set parameters)
    cal = Calibration()

    ###readout pulse##############################################################
    if param_dict["ro_power"] >= param_dict["cav_drive_power"]:
        ro_power_range, dummy_amp = shfqa_power_calculator(param_dict["ro_power"])
    else:
        ro_power_range, dummy_amp = shfqa_power_calculator(
            param_dict["cav_drive_power"]
        )
    # define oscillator parameters for the readout pulse
    ro_signal_amp = 10 ** ((param_dict["ro_power"] - ro_power_range) / 20)
    cav_drive_amp = 10 ** ((param_dict["cav_drive_power"] - ro_power_range) / 20)
    sample1 = int(2e9 * param_dict["cav_drive_length"])  # cavity pulse
    sample2 = int(2e9 * param_dict["ro_pulse_length"])  # measure pulse
    # define the readout pulse shape
    ro_pulse = pulse_library.PulseSampled(
        uid="ro_pulse",
        samples=(
            np.concatenate(
                [cav_drive_amp * np.ones(sample1), ro_signal_amp * np.ones(sample2)]
            )
        ),
    )
    # define an readout if and lo frequency
    ro_if_oscillator = Oscillator(
        frequency=param_dict["ro_freq"] - param_dict["ro_lo_freq"],
    )
    ro_lo_oscillator = Oscillator(frequency=param_dict["ro_lo_freq"])

    cal["measure"] = SignalCalibration(
        oscillator=ro_if_oscillator,
        local_oscillator=ro_lo_oscillator,
        range=ro_power_range,
        # amplitude=1.0
    )
    cal["acquire"] = SignalCalibration(
        oscillator=ro_if_oscillator,
        local_oscillator=ro_lo_oscillator,
        range=param_dict["ro_acquire_range"],
        port_delay=0,  ##### Have to consider if this is the best way (Taketo)
    )

    ###qubit pulse##############################################################
    # define the qubit drive pulse length and shape
    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_power"])
    qu_signal_amp = 10 ** ((param_dict["qu_power"] - qu_power_range) / 20)
    qu_freq_sweep = LinearSweepParameter(
        uid="qu_freq_sweep",
        start=param_dict["pulsed_acStark_shift"]["qu_freq_start"]
        - param_dict["qu_lo_freq"],
        stop=param_dict["pulsed_acStark_shift"]["qu_freq_stop"]
        - param_dict["qu_lo_freq"],
        count=param_dict["pulsed_acStark_shift"]["qu_freq_npts"],
        axis_name="Qubit drive frequency [Hz]",
    )
    qu_drive_pulse = pulse_library.gaussian_square(
        uid="qu_pulse",
        length=param_dict["qu_pi_pulse_length"] + 20e-9,
        width=param_dict["qu_pi_pulse_length"],
        amplitude=qu_signal_amp,
    )
    # define an qubit drive if and lo frequency
    qu_if_oscillator = Oscillator(
        frequency=qu_freq_sweep, modulation_type=ModulationType.HARDWARE
    )
    qu_lo_oscillator = Oscillator(
        frequency=param_dict["qu_lo_freq"], modulation_type=ModulationType.AUTO
    )
    # define an oscillator for the qubit drive pulse
    cal["qu_drive"] = SignalCalibration(
        oscillator=qu_if_oscillator,
        local_oscillator=qu_lo_oscillator,
        range=qu_power_range,
    )

    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)
    #####################################################################

    # check if maximum memory would be reached(???? by Taketo)
    execution_type = ExecutionType.REAL_TIME
    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="pulsed_acStark_shift",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
    ):
        # inner loop - real time sweep of Rabi amplitudes
        with exp.sweep(
            uid="qu_freq_sweep", parameter=qu_freq_sweep, execution_type=execution_type
        ):
            with exp.section(
                uid="excitation",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                on_system_grid=False,
                length=param_dict["cav_drive_length"],
            ):
                exp.play(signal="qu_drive", pulse=qu_drive_pulse)
            # measurement
            with exp.section(uid="readout", alignment=SectionAlignment.RIGHT):
                exp.play("measure", pulse=ro_pulse)
                exp.acquire(
                    "acquire",
                    length=param_dict["ro_pulse_length"],
                    handle="exp_measure_handle",
                )
            with exp.section(
                uid="reset", alignment=SectionAlignment.LEFT, play_after="readout"
            ):
                exp.delay("qu_drive", time=param_dict["reset_delay"])

    return exp
