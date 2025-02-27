"""@author Taketo
Pulsed twotone spectroscopy vs qubit power

Instrument
----------
SHFQC: for readout pulse
HDAWG: for qubit pulse envelope
R&S SGS100a : for upconvertion of qubit pulse

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
        "qu_drive": "/logical_signal_groups/q0/hdawg_drive",
    }
    exp.set_signal_map(signal_map)
    # define an experiment calibration (set parameters)
    cal = Calibration()
    ##############ro pulse##########################################################
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
    ##############qu pulse###########################################################
    qu_drive_pulse = pulse_library.cos2(
        uid="qu_pulse",
        length=param_dict["qu_pulse_length"],
        amplitude=param_dict["qu_pulse_amp"],
    )
    # define an oscillator for the qubit drive pulse
    cal["qu_drive"] = SignalCalibration(
        oscillator=None, local_oscillator=None, range=param_dict["qu_power_range"]
    )

    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)

    # check if maximum memory would be reached(???? by Taketo)
    execution_type = ExecutionType.REAL_TIME
    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="pulsed_twotone",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
    ):
        # qubit drive
        with exp.section(
            uid="excitation",
            alignment=SectionAlignment.RIGHT,
            trigger=None,
            on_system_grid=True,
        ):
            exp.play(
                signal="qu_drive",
                pulse=qu_drive_pulse,
                length=param_dict[
                    "qu_pulse_length"
                ],  # is this length argument necessary??by Taketo
            )
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
