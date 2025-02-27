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
            ExperimentSignal("cav_drive"),  # cavity drive pulse
        ],
    )

    # define the signal mapping between the LogicalSignals and the ExperimentSignals
    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        "qu_drive": "/logical_signal_groups/q0/shfqc_drive",
        "cav_drive": "/logical_signal_groups/q0/shfqc_drive_cav",
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
    if param_dict["qu_power"] >= param_dict["cav_drive_power"]:
        drive_lo_range, dummy_amp = shfqa_power_calculator(param_dict["qu_power"])
    else:
        drive_lo_range, dummy_amp = shfqa_power_calculator(
            param_dict["cav_drive_power"]
        )
    # define the qubit drive pulse length and shape
    # qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_power"])
    qu_signal_amp = 10 ** ((param_dict["qu_power"] - drive_lo_range) / 20)
    qu_power_range = drive_lo_range
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

    ###cav drive pulse##############################################################
    # if param_dict["cav_drive_power"] > qu_power_range:
    # raise ValueError(f'"cav_drive_power"should be smaller than LO power range "{qu_power_range}" or needs to change codes.')
    # cav_drive_amp =10**((param_dict["cav_drive_power"]-qu_power_range)/20) #the same output port must have the same range!!

    cav_drive_amp = 10 ** ((param_dict["cav_drive_power"] - drive_lo_range) / 20)
    # if ef power > qu_power_range, return errormplitude=cav_drive_amp,
    # )
    cav_drive_pulse = pulse_library.gaussian_square(
        uid="cav_drive_pulse",
        length=param_dict["cav_drive_length"] + 20e-9,
        width=param_dict["cav_drive_length"],
        amplitude=cav_drive_amp,
    )
    # dcav_driveine an qubit cav_drive drive if and lo frequency
    cav_drive_if_oscillator = Oscillator(
        frequency=param_dict["cav_drive_freq"] - param_dict["qu_lo_freq"],
        modulation_type=ModulationType.HARDWARE,
    )
    # cav_drive_lo_oscillator = Oscillator(
    #                     frequency=param_dict["cav_drive_lo_freq"],
    #                     modulation_type=ModulationType.AUTO
    #                     )
    # dcav_driveine an oscillator for the qubit cav_drive drive pulse
    cal["cav_drive"] = SignalCalibration(
        oscillator=cav_drive_if_oscillator,
        local_oscillator=qu_lo_oscillator,
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
            # cavity drive + qubit drive
            with exp.section(
                uid="excitation",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                on_system_grid=True,
            ):
                # exp.play(
                # signal="qu_drive",
                # pulse=qu_drive_pulse,
                # length=param_dict["pulsed_acStark_shift"]["qu_pulse_length"], # is this length argument necessary??by Taketo
                # )
                exp.play(signal="qu_drive", pulse=qu_drive_pulse)
                exp.play(signal="cav_drive", pulse=cav_drive_pulse)
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
