"""@author Taketo

This makes an experimental(only valid for this measurement) calibration object,
map the signals
and run the experiment saving the data with DDH5 Writer

"""

import matplotlib.pyplot as plt
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

    # define the readout pulse shape
    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=param_dict["ro_pulse_length"],
        amplitude=1.0,  # should be 1.0 always
    )

    # define the qubit drive pulse length and shape
    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_drive_power"])
    qu_freq_sweep = LinearSweepParameter(
        uid="qu_freq_sweep",
        start=param_dict["qu_freq_start"] - param_dict["qu_lo_freq"],
        stop=param_dict["qu_freq_stop"] - param_dict["qu_lo_freq"],
        count=param_dict["qu_freq_npts"],
        axis_name="Qubit drive frequency [Hz]",
    )

    pwm_pulse_freq = param_dict["qu_drive_pwm_freq"]
    pwm_pulse_amp = qu_signal_amp
    pwm_pulse_length = param_dict["qu_pulse_length"]
    sampling_rate = 2e9
    target_pulse = pulse_library.cos2(
        uid="ge_pulse", length=pwm_pulse_length, amplitude=pwm_pulse_amp
    )
    timearray, env_array = target_pulse.generate_sampled_pulse()
    env_array = env_array.real  # envelope doesn't have imag
    oscillating_array = np.array(
        [
            np.exp(-1j * 2 * np.pi * pwm_pulse_freq * k / sampling_rate)
            for k in range(int(pwm_pulse_length * sampling_rate))
        ]
    )

    pwm_array = env_array * oscillating_array
    qu_drive_pulse_pwm = pulse_library.sampled_pulse_complex(
        uid="cos_pwm_pulse", samples=pwm_array
    )
    qu_drive_pulse = qu_drive_pulse_pwm

    plt.figure()
    plt.plot(qu_drive_pulse.samples.real, label="pwm_real")
    plt.plot(qu_drive_pulse.samples.imag, label="pwm_imag")
    plt.xlabel("time [ns]")
    plt.ylabel("envelope [arb]")
    plt.legend()

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
        uid="pulsed_twotone",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
    ):
        # inner loop - real time sweep of Rabi amplitudes
        with exp.sweep(
            uid="qu_freq_sweep", parameter=qu_freq_sweep, execution_type=execution_type
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
