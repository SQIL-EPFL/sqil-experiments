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
        "qu_drive": "/logical_signal_groups/q0/hdawg_drive",
    }
    exp.set_signal_map(signal_map)

    # define an experiment calibration (set parameters)
    cal = Calibration()

    #########ro pulse###################################################
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

    ###########qu pulse###################################################
    # define the half pi pulse/ pi pulse length and shape
    qu_half_pi_pulse = pulse_library.cos2(
        uid="qu_half_pi_pulse",
        length=param_dict["qu_pi_pulse_length"],
        amplitude=param_dict["qu_pulse_amp"] / 2,  # is it correct??(taketo)
    )

    qu_pi_pulse = pulse_library.cos2(
        uid="qu_pi_pulse",
        length=param_dict["qu_pi_pulse_length"],
        amplitude=param_dict["qu_pulse_amp"],
    )

    # define an oscillator for the qubit drive pulse
    cal["qu_drive"] = SignalCalibration(
        oscillator=None, local_oscillator=None, range=param_dict["qu_power_range"]
    )
    # define an ramsey delay sweep
    if param_dict["logsweep"] == True:
        # define an readout delay sweep
        interval_sweep = SweepParameter(
            uid="interval_sweep",
            values=param_dict["interval_sweep_list"],
            axis_name="Pulse interval delay [sec]",
        )
    else:
        interval_sweep = LinearSweepParameter(
            uid="interval_sweep",
            start=param_dict["interval_sweep_start"],
            stop=param_dict["interval_sweep_stop"],
            count=param_dict["interval_sweep_npts"],
            axis_name="Pulse interval delay [sec]",
        )

    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)
    #####################################################################

    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="echo_cpmg_shots",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
    ):
        # inner loop - real time sweep of Ramsey time delays
        with exp.sweep(
            uid="interval_sweep",
            parameter=interval_sweep,
            alignment=SectionAlignment.RIGHT,
            # repetition_mode=RepetitionMode.AUTO, # will make all of the repetition rate fixed (make measurement longer)
        ):
            # play qubit excitation pulse - pulse amplitude is swept
            with exp.section(
                uid="excitation",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
            ):
                exp.play(signal="qu_drive", pulse=qu_half_pi_pulse)
                # 2*N-1 pi pulses
                rep = 2 * param_dict["pi_pulse_rep"] - 1
                for _ in range(rep):
                    exp.delay(signal="qu_drive", time=interval_sweep / 2 / rep)
                    exp.play(signal="qu_drive", pulse=qu_pi_pulse)
                    exp.delay(signal="qu_drive", time=interval_sweep / 2 / rep)
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
