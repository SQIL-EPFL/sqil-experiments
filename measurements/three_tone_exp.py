"""@author Taketo

This makes an experimental(only valid for this measurement) calibration object,
map the signals
and run the experiment saving the data with DDH5 Writer

"""

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
        "qu_drive_ef": "/logical_signal_groups/q0/shfqc_drive_ef",
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
    # qu_pi_pulse = pulse_library.cos2(
    # uid="qu_pulse",
    # length=param_dict["qu_pi_pulse_length"],
    # amplitude=qu_signal_amp,
    # )
    qu_pi_pulse = pulse_library.gaussian_square(
        uid="qu_pulse",
        length=param_dict["qu_pi_pulse_length"] + 20e-9,
        width=param_dict["qu_pi_pulse_length"],
        amplitude=qu_signal_amp,
    )
    # define an qubit drive if and lo frequency
    qu_if_oscillator = Oscillator(
        frequency=param_dict["qu_freq"] - param_dict["qu_lo_freq"],
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

    ###qubit ef drive##############################################################
    if param_dict["ef_drive_power"] > qu_power_range:
        raise ValueError(
            f'"ef_drive_power"should be smaller than LO power range "{qu_power_range}" or needs to change codes.'
        )
    ef_signal_amp = 10 ** (
        (param_dict["ef_drive_power"] - qu_power_range) / 20
    )  # the same output port must have the same range!!
    # if ef power > qu_power_range, return error
    # ef_pulse = pulse_library.cos2(
    # uid="ef_pulse",
    # length=param_dict["ef_pulse_length"],
    # amplitude=ef_signal_amp,
    # )
    ef_pulse = pulse_library.gaussian_square(
        uid="ef_pulse",
        length=param_dict["ef_pulse_length"] + 20e-9,
        width=param_dict["ef_pulse_length"],
        amplitude=ef_signal_amp,
    )
    # define the qubit drive pulse length and shape
    ef_if_freq_sweep = LinearSweepParameter(
        uid="ef_if_freq_sweep",
        start=param_dict["pulsed_threetone"]["ef_freq_start"]
        - param_dict["qu_lo_freq"],
        stop=param_dict["pulsed_threetone"]["ef_freq_stop"] - param_dict["qu_lo_freq"],
        count=param_dict["pulsed_threetone"]["ef_freq_npts"],
        axis_name="Qubit ef IF frequency [Hz]",
    )
    # define an qubit ef drive if and lo frequency
    ef_if_oscillator = Oscillator(
        frequency=ef_if_freq_sweep, modulation_type=ModulationType.HARDWARE
    )
    # ef_lo_oscillator = Oscillator(
    #                     frequency=param_dict["ef_lo_freq"],
    #                     modulation_type=ModulationType.AUTO
    #                     )
    # define an oscillator for the qubit ef drive pulse
    cal["qu_drive_ef"] = SignalCalibration(
        oscillator=ef_if_oscillator,
        # local_oscillator = ef_lo_oscillator, # the same output port must use the same local oscillator setting
        # range = ef_power_range # the same output port must use the same local oscillator setting
    )

    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)

    ###############################################################################
    # check if maximum memory would be reached(???? by Taketo)
    execution_type = ExecutionType.REAL_TIME
    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="three_tone",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
        repetition_mode=RepetitionMode.AUTO,
    ):
        # inner loop - real time sweep of T1 time delays
        with exp.sweep(
            uid="ef_freq_sweep",
            parameter=ef_if_freq_sweep,
            alignment=SectionAlignment.RIGHT,
        ):
            # play qubit excitation pulse - pulse amplitude is swept
            with exp.section(
                uid="ge_excitation",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                on_system_grid=True,
            ):
                exp.play(signal="qu_drive", pulse=qu_pi_pulse)
            with exp.section(
                uid="ef_drive",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                play_after="ge_excitation",
                on_system_grid=True,
            ):
                exp.play(signal="qu_drive_ef", pulse=ef_pulse)
                # measurement
            with exp.section(uid="readout", play_after="ef_drive"):
                exp.measure(
                    measure_signal="measure",
                    measure_pulse=ro_pulse,
                    handle="exp_measure_handle",
                    acquire_signal="acquire",
                    integration_length=param_dict["ro_pulse_length"],
                    reset_delay=param_dict["reset_delay"],
                )

    return exp
