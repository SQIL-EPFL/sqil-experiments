"""@author Taketo

This makes an experimental(only valid for this measurement) calibration object,
map the signals
and run the experiment saving the data with DDH5 Writer

"""

import numpy as np
from helpers.utilities import shfqa_power_calculator
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
        ],
    )

    # define the signal mapping between the LogicalSignals and the ExperimentSignals
    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        "qu_drive": "/logical_signal_groups/q0/shfqc_drive",
    }
    exp.set_signal_map(signal_map)

    ################## Calibration (parameter setting) ##################
    # define an experiment calibration (set parameters)
    cal = Calibration()

    ### readout pulse
    # define an readout if and lo frequency
    ro_if_oscillator = Oscillator(
        frequency=param_dict["qu_freq"] - param_dict["ro_lo_freq"]
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

    # define the readout pulse shape
    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=param_dict["ro_pulse_length"],
        amplitude=1.0,  # should be 1.0 always
    )

    ### qubit drive pulse, pi-pulse
    # define an qubit drive if and lo frequency
    qu_if_oscillator = Oscillator(
        frequency=param_dict["qu_freq"] - param_dict["qu_lo_freq"],
        modulation_type=ModulationType.HARDWARE,
    )
    qu_lo_oscillator = Oscillator(
        frequency=param_dict["qu_lo_freq"], modulation_type=ModulationType.AUTO
    )
    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_drive_power"])
    # define an oscillator for the qubit drive pulse
    cal["qu_drive"] = SignalCalibration(
        oscillator=qu_if_oscillator,
        local_oscillator=qu_lo_oscillator,
        range=qu_power_range,
    )

    # define the half pi pulse length and shape
    qu_pi_pulse = pulse_library.cos2(
        uid="qu_half_pi_pulse",
        length=param_dict["qu_pi_pulse_length"],
        amplitude=qu_signal_amp,
    )

    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)
    #####################################################################

    ## define experimental sequence
    # take n single shots without averaging
    with exp.acquire_loop_rt(
        uid="ground_state_n_shots",
        count=2**16,  # what effect does this have for the RAW mode???
        averaging_mode=AveragingMode.CYCLIC,  # SINGLE_SHOT,
        acquisition_type=AcquisitionType.RAW,
        repetition_mode=RepetitionMode.AUTO,
    ):

        # play delay pulse equivalent to excitation pulse
        with exp.section(
            uid="ground_delay",
            alignment=SectionAlignment.RIGHT,
            trigger=None,
            on_system_grid=True,
        ):
            exp.delay(signal="qu_drive", time=param_dict["qu_pi_pulse_length"])

        # measurement
        with exp.section(uid="ground_readout", play_after="ground_delay"):
            """
            exp.measure(
                 measure_signal="measure",
                 measure_pulse=ro_pulse,
                 handle="ground_state",
                 acquire_signal="acquire",
                 integration_length=param_dict["ro_pulse_length"],
                 reset_delay=param_dict["reset_delay"],
                 )
            """

            # separate measurement in acquire and measurement pulse sequence

            exp.acquire(
                handle="ground_state",
                signal="acquire",
                length=200e-9 + param_dict["ro_pulse_length"] + 400e-9,
            )
            exp.delay(signal="measure", time=200e-9)
            exp.play(
                signal="measure",
                pulse=ro_pulse,
            )
            exp.delay(signal="measure", time=param_dict["reset_delay"])

        # play excitation pulse
        with exp.section(
            uid="qubit_excitation",
            play_after="ground_readout",
            alignment=SectionAlignment.RIGHT,
            trigger=None,
            on_system_grid=True,
        ):
            exp.play(
                signal="qu_drive",
                pulse=qu_pi_pulse,
                length=param_dict["qu_pi_pulse_length"],
            )

        # measurement
        with exp.section(uid="excited_readout", play_after="qubit_excitation"):
            """
            exp.measure(
                measure_signal="measure",
                measure_pulse=ro_pulse,
                handle="excited_state",
                acquire_signal="acquire",
                integration_length=param_dict["ro_pulse_length"],
                reset_delay=param_dict["reset_delay"],
                )
            """

            # separate measurement in acquire and measurement pulse sequence

            exp.acquire(
                handle="excited_state",
                signal="acquire",
                length=200e-9 + param_dict["ro_pulse_length"] + 400e-9,
            )
            exp.delay(signal="measure", time=200e-9)
            exp.play(
                signal="measure",
                pulse=ro_pulse,
            )
            exp.delay(signal="measure", time=param_dict["reset_delay"])

    return exp
