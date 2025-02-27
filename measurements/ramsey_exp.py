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
    # define the readout pulse shape
    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=param_dict["ro_pulse_length"],
        amplitude=1.0,  # should be 1.0 always
    )
    # define an readout if and lo frequency
    ro_if_oscillator = Oscillator(
        frequency=param_dict["ro_freq"] - param_dict["ro_lo_freq"],
    )
    ro_lo_oscillator = Oscillator(frequency=param_dict["ro_lo_freq"])
    # define oscillator parameters for the readout pulse
    ro_power_range, ro_signal_amp = shfqa_power_calculator(param_dict["ro_power"])

    cal["measure"] = SignalCalibration(
        oscillator=ro_if_oscillator,
        local_oscillator=ro_lo_oscillator,
        range=ro_power_range,
        amplitude=ro_signal_amp,
    )
    cal["acquire"] = SignalCalibration(
        oscillator=ro_if_oscillator,
        local_oscillator=ro_lo_oscillator,
        range=param_dict["ro_acquire_range"],
        port_delay=0,  ##### Have to consider if this is the best way (Taketo)
    )

    ###qubit ge pi pulse##############################################################
    # define the qubit drive pulse length and shape
    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_power"])
    # qu_half_pi_pulse = pulse_library.cos2(
    # uid="qu_half_pi_pulse",
    # length=param_dict["qu_pi_pulse_length"],
    # amplitude=qu_signal_amp/2,# is it correct??(taketo)
    # )
    qu_half_pi_pulse = pulse_library.gaussian_square(
        uid="qu_half_pi_pulse",
        length=param_dict["qu_pi_pulse_length"] + 20e-9,
        width=param_dict["qu_pi_pulse_length"],
        amplitude=qu_signal_amp / 2,
    )
    # define an qubit drive if and lo frequency
    qu_if_oscillator = Oscillator(
        frequency=param_dict["qu_freq"]
        - param_dict["qu_lo_freq"]
        + param_dict["qu_freq_detune"],
        modulation_type=ModulationType.HARDWARE,
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

    ###############################################################################
    # define an interval delay sweep
    interval_sweep = LinearSweepParameter(
        uid="interval_sweep",
        start=param_dict["ramsey"]["interval_sweep_start"],
        stop=param_dict["ramsey"]["interval_sweep_stop"],
        count=param_dict["ramsey"]["interval_sweep_npts"],
        axis_name="Pulse interval delay [sec]",
    )
    ###############################################################################

    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="ramsey_shots",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
        # repetition_mode=RepetitionMode.AUTO,
    ):
        # inner loop - real time sweep of Ramsey time delays
        with exp.sweep(
            uid="ramsey_sweep",
            parameter=interval_sweep,
            alignment=SectionAlignment.RIGHT,
        ):
            # play qubit excitation pulse - pulse amplitude is swept
            with exp.section(
                uid="excitation",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                on_system_grid=True,
            ):
                exp.play(signal="qu_drive", pulse=qu_half_pi_pulse)
                exp.delay(signal="qu_drive", time=interval_sweep)
                exp.play(signal="qu_drive", pulse=qu_half_pi_pulse)
                exp.delay(signal="qu_drive", time=param_dict["readout_delay"])

            # measurement
            with exp.section(uid="readout", play_after="excitation"):
                exp.measure(
                    measure_signal="measure",
                    measure_pulse=ro_pulse,
                    handle="exp_measure_handle",
                    acquire_signal="acquire",
                    integration_length=param_dict["ro_pulse_length"],
                    reset_delay=param_dict["reset_delay"],
                )
    return exp
