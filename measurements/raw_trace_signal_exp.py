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
            # ExperimentSignal("qu_drive"), # needs to be removed when not using SHFQC SG channels!
        ],
    )

    # define the signal mapping between the LogicalSignals and the ExperimentSignals
    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        # "qu_drive": "/logical_signal_groups/q0/shfqc_drive" # needs to be removed when not using SHFQC SG channels!
    }
    exp.set_signal_map(signal_map)

    # define the readout pulse shape
    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=param_dict["ro_pulse_length"],
        amplitude=1.0,  # should be 1.0 always
    )

    ################## Calibration (parameter setting) ##################
    # define an experiment calibration (set parameters)
    cal = Calibration()
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
    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)
    #####################################################################

    # check if maximum memory would be reached(???? by Taketo)
    execution_type = ExecutionType.REAL_TIME
    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="RAW_onetone",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.RAW,
    ):
        # measurement
        with exp.section(
            uid="readout",
        ):
            exp.play(
                signal="measure",
                pulse=ro_pulse,
            )
            exp.delay(signal="acquire", time=param_dict["acquire_delay"])
            exp.acquire(
                signal="acquire",
                handle="exp_measure_handle",
                # kernel=ro_pulse,
                length=param_dict["ro_pulse_length"] - param_dict["acquire_delay"],
            )
            exp.delay(signal="acquire", time=param_dict["reset_delay"])

            # exp.measure(
            # measure_signal="measure",
            # measure_pulse=ro_pulse,
            # handle="exp_measure_handle",
            # acquire_signal="acquire",
            # acquire_delay=param_dict["acquire_delay"],
            # integration_length=param_dict["ro_pulse_length"],
            # reset_delay=param_dict["reset_delay"],
            # )

    return exp
