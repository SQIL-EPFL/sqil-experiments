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


def main_exp(session, param_dict, writer, ro_power):
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

    # define the readout pulse shape
    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=param_dict["ro_pulse_length"],
        amplitude=1.0,  # should be 1.0 always
    )

    # define the qubit drive pulse length and shape
    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_drive_power"])
    qu_pulse_length_sweep = LinearSweepParameter(
        uid="qu_pulse_length_sweep",
        start=param_dict["qu_pulse_length_start"],
        stop=param_dict["qu_pulse_length_stop"],
        count=param_dict["qu_pulse_length_npts"],
        axis_name="Pulse length [sec]",
    )
    qu_drive_pulse = pulse_library.cos2(
        uid="qu_pulse",
        length=qu_pulse_length_sweep,
        amplitude=0.78,
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
    ro_power_range, ro_signal_amp = shfqa_power_calculator(ro_power)
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
        oscillator=qu_if_oscillator, local_oscillator=qu_lo_oscillator, range=-10
    )

    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)
    #####################################################################

    # def data_upload(session, handle, writer, param_dict, qu_pulse_length, ro_power):
    # """
    # acquire and upload to DDH5 file the latest loop results.
    # """
    # results = session.results
    # last_result_index = results.get_last_nt_step(handle)
    # last_result = results.get_data(handle)[last_result_index]
    # writer.add_data(
    # qu_pulse_length=qu_pulse_length,
    # power=ro_power,
    # data=last_result
    # )
    # session.register_neartime_callback(data_upload)

    # check if maximum memory would be reached(???? by Taketo)
    execution_type = ExecutionType.REAL_TIME
    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="rabi_shots",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
    ):
        # inner loop - real time sweep of Rabi amplitudes
        with exp.sweep(
            uid="rabi_sweep",
            parameter=qu_pulse_length_sweep,
            execution_type=execution_type,
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
                    length=qu_pulse_length_sweep,
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
