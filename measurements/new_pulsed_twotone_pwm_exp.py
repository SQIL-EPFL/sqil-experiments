"""@author Taketo

This makes an experimental (only valid for this measurement) calibration object,
map the signals
and run the experiment saving the data with DDH5 Writer
"""

import matplotlib.pyplot as plt
import numpy as np
from helpers.utils import shfqa_power_calculator
from laboneq.simple import *
from laboneq_applications.qpu_types.tunable_transmon import TunableTransmonQubit

setup_file = __file__

qf = 5.3290e9
param_dict = {
    "ro_pulse_length": 3e-6,
    "ro_freq": 7.6174e9,
    "ro_lo_freq": 7.2e9,
    "ro_power": -30,
    "ro_acquire_range": -20,
    "qu_pulse_length": 2000e-9,
    "qu_freq_start": qf - 10e6,
    "qu_freq_stop": qf + 10e6,
    "qu_freq_npts": 101,
    "qu_lo_freq": 5.0e9,
    "qu_power": -20,
    "qu_drive_pwm_freq": 0e6,
    "reset_delay": 1e-6,
    "external_avg": 1,
    "plot_fit": True,
    "save_pulsesheet": True,
    "avg": 2000,
}


def main_exp(session, qubit: TunableTransmonQubit, settings, writer):
    exp = Experiment(
        uid="exp",
        signals=[
            ExperimentSignal("measure"),
            ExperimentSignal("acquire"),
            ExperimentSignal("drive"),
        ],
    )

    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        "drive": "/logical_signal_groups/q0/shfqc_drive",
    }
    exp.set_signal_map(signal_map)

    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=qubit.parameters.readout_length,
        amplitude=1.0,
    )

    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_power"])
    qu_freq_sweep = LinearSweepParameter(
        uid="qu_freq_sweep",
        start=param_dict["qu_freq_start"] - qubit.parameters.drive_lo_frequency,
        stop=param_dict["qu_freq_stop"] - qubit.parameters.drive_lo_frequency,
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
    env_array = env_array.real
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

    plt.figure()
    plt.plot(qu_drive_pulse_pwm.samples.real, label="pwm_real")
    plt.plot(qu_drive_pulse_pwm.samples.imag, label="pwm_imag")
    plt.xlabel("time [ns]")
    plt.ylabel("envelope [arb]")
    plt.legend()

    ################## Calibration ##################
    cal = Calibration()

    ro_if_oscillator = Oscillator(
        frequency=qubit.parameters.readout_resonator_frequency
        - qubit.parameters.readout_lo_frequency
    )
    ro_lo_oscillator = Oscillator(frequency=qubit.parameters.readout_lo_frequency)

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
        port_delay=0,
    )

    qu_if_oscillator = Oscillator(
        frequency=qu_freq_sweep,
        modulation_type=ModulationType.HARDWARE,
    )
    qu_lo_oscillator = Oscillator(
        frequency=qubit.parameters.drive_lo_frequency,
        modulation_type=ModulationType.AUTO,
    )

    cal["drive"] = SignalCalibration(
        oscillator=qu_if_oscillator,
        local_oscillator=qu_lo_oscillator,
        range=qu_power_range,
    )

    exp.set_calibration(cal)
    ##################################################

    execution_type = ExecutionType.REAL_TIME
    from laboneq_applications.qpu_types.tunable_transmon import (
        TunableTransmonOperations,
        TunableTransmonQubit,
    )

    qop = TunableTransmonOperations()

    @dsl.quantum_operation
    def x180(qop, q):
        dsl.play(signal="drive", pulse=qu_drive_pulse_pwm)

    @dsl.quantum_operation
    def readout(qop, q):
        dsl.measure(
            measure_signal="measure",
            measure_pulse=ro_pulse,
            handle="exp_measure_handle",
            acquire_signal="acquire",
            integration_length=param_dict["qu_pulse_length"],
            reset_delay=qubit.parameters.reset_delay_length,
        )

    qop.register(x180)
    qop.register(readout)

    with exp.acquire_loop_rt(
        uid="pulsed_twotone",
        count=settings.external_avg,
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
    ):
        with exp.sweep(
            uid="qu_freq_sweep", parameter=qu_freq_sweep, execution_type=execution_type
        ):
            with exp.section(
                uid="excitation",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                on_system_grid=True,
            ):
                qop.x180(qubit)

            with exp.section(uid="readout", play_after="excitation"):
                qop.readout(qubit)

    return exp
