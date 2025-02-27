"""
@author Taketo

This makes an experimental(only valid for this measurement) calibration object,
map the signals
and run the experiment saving the data with DDH5 Writer
"""

import numpy as np
from helpers.utilities import create_pwm_array, shfqa_power_calculator
from laboneq.simple import *
from plottr.data.qipe_datadict_storage import DataDict, DDH5Writer

setup_file = __file__


def main_exp(session, param_dict, writer):
    # create exp object and define the ExperimentSignal lines
    exp = Experiment(
        uid="exp",
        signals=[
            ExperimentSignal("measure"),
            ExperimentSignal("acquire"),
            ExperimentSignal("qu_drive"),
            ExperimentSignal("qu_drive_ef"),
        ],
    )
    # define an experiment calibration (set parameters)
    cal = Calibration()

    # define the signal mapping between the LogicalSignals and the ExperimentSignals
    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        "qu_drive": "/logical_signal_groups/q0/shfqc_drive",
        # "qu_drive_ef":"/logical_signal_groups/q0/shfqc_drive_ef",
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
        frequency=param_dict["ro_freq"] - param_dict["ro_lo_freq"]
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

    ###qubit ge+ef pulse##############################################################
    # qubit if + lo frequency = medium point between ge and ef freq
    qu_if_lo_freq = (param_dict["qu_freq"] + param_dict["ef_freq"]) / 2

    qu_power_range, ge_pi_amp = shfqa_power_calculator(param_dict["qu_drive_power"])
    qu_ge_pi_array = crete_pwm_array(
        pwm_freq=param_dict["qu_freq"] - qu_if_lo_freq,
        pulse_length=param_dict["qu_pi_pulse_length"],
        pulse_amp=ge_pi_amp,
    )

    # define ef drive pulse length sweep
    ef_pulse_length_sweep = LinearSweepParameter(
        uid="ef_pulse_length_sweep",
        start=param_dict["ef_pulse_length_start"],
        stop=param_dict["ef_pulse_length_stop"],
        count=param_dict["ef_pulse_length_npts"],
        axis_name="Pulse length [sec]",
    )

    if param_dict["ef_drive_power"] > qu_power_range:
        raise ValueError(
            f'"ef_drive_power"should be smaller than LO power range "{qu_power_range}" or needs to change codes.'
        )
    ef_signal_amp = 10 ** (
        (param_dict["ef_drive_power"] - qu_power_range) / 20
    )  # the same output port must have the same range!!
    # if ef power > qu_power_range, return error
    qu_ef_array = crete_pwm_array(
        pwm_freq=param_dict["ef_freq"] - qu_if_lo_freq,
        pulse_length=ef_pulse_length_sweep,
        pulse_amp=ef_signal_amp,
    )

    # merge ge pi pulse and ef drive signal array
    pulse_array = np.concatenate([qu_ge_pi_array, qu_ef_array])
    qu_pulse = pulse_library.sampled_pulse_complex(
        uid="cos_gf_pwm_pulse",
        samples=pulse_array,
    )
    # define an qubit drive if and lo frequency
    qu_if_oscillator = Oscillator(
        frequency=qu_if_lo_freq - param_dict["qu_lo_freq"],
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

    ###############################################################################
    # check if maximum memory would be reached(???? by Taketo)
    execution_type = ExecutionType.REAL_TIME
    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="time_rabi_ef",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
        # repetition_mode=RepetitionMode.AUTO,
    ):
        # inner loop - real time sweep of T1 time delays
        with exp.sweep(
            uid="ef_pulse_length_sweep",
            parameter=ef_pulse_length_sweep,
            alignment=SectionAlignment.RIGHT,
            execution_type=execution_type,
        ):
            # play qubit excitation pulse - pulse amplitude is swept
            with exp.section(
                uid="qu_drive",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                on_system_grid=True,
            ):
                exp.play(
                    signal="ge_ef_drive",
                    pulse=qu_pulse,
                    length=param_dict["qu_pi_pulse_length"] + ef_pulse_length_sweep,
                )
            with exp.section(uid="readout", play_after="qu_drive"):
                exp.measure(
                    measure_signal="measure",
                    measure_pulse=ro_pulse,
                    handle="exp_measure_handle",
                    acquire_signal="acquire",
                    integration_length=param_dict["ro_pulse_length"],
                    reset_delay=param_dict["reset_delay"],
                )

    return exp
