"""@author Taketo

This makes an experimental (only valid for this measurement) calibration object,
map the signals
and run the experiment saving the data with DDH5 Writer
"""

import matplotlib.pyplot as plt
import numpy as np
from helpers.utilities import shfqa_power_calculator
from laboneq.simple import *
from laboneq.dsl import play, measure
from laboneq.simple import qpu

setup_file = __file__

def main_exp(session, qubit, settings, writer):
    exp = Experiment(
        uid="exp",
        signals=[
            ExperimentSignal("measure"),
            ExperimentSignal("acquire"),
            ExperimentSignal("qu_drive"),
        ],
    )

    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        "qu_drive": "/logical_signal_groups/q0/shfqc_drive",
    }
    exp.set_signal_map(signal_map)

    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=qubit.ro_pulse_length,
        amplitude=1.0,
    )

    qu_power_range, qu_signal_amp = shfqa_power_calculator(qubit.qu_drive_power)
    qu_freq_sweep = LinearSweepParameter(
        uid="qu_freq_sweep",
        start=qubit.qu_freq_start - qubit.qu_lo_freq,
        stop=qubit.qu_freq_stop - qubit.qu_lo_freq,
        count=qubit.qu_freq_npts,
        axis_name="Qubit drive frequency [Hz]",
    )

    pwm_pulse_freq = qubit.qu_drive_pwm_freq
    pwm_pulse_amp = qu_signal_amp
    pwm_pulse_length = qubit.qu_pulse_length
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
        frequency=qubit.ro_freq - qubit.ro_lo_freq
    )
    ro_lo_oscillator = Oscillator(
        frequency=qubit.ro_lo_freq
    )

    ro_power_range, ro_signal_amp = shfqa_power_calculator(qubit.ro_power)

    cal["measure"] = SignalCalibration(
        oscillator=ro_if_oscillator,
        local_oscillator=ro_lo_oscillator,
        range=ro_power_range,
        amplitude=ro_signal_amp,
    )
    cal["acquire"] = SignalCalibration(
        oscillator=ro_if_oscillator,
        local_oscillator=ro_lo_oscillator,
        range=qubit.ro_acquire_range,
        port_delay=0,
    )

    qu_if_oscillator = Oscillator(
        frequency=qu_freq_sweep,
        modulation_type=ModulationType.HARDWARE,
    )
    qu_lo_oscillator = Oscillator(
        frequency=qubit.qu_lo_freq,
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

    qop = qpu.QuantumOperations()

    def x180(qop, q):
        play(signal="drive", pulse=qu_drive_pulse_pwm)

    def readout(qop, q):
        measure(
            measure_signal="measure",
            measure_pulse=ro_pulse,
            handle="exp_measure_handle",
            acquire_signal="acquire",
            integration_length=qubit.qu_pulse_length,
            reset_delay=qubit.reset_delay,
        )

    qop.register(x180)
    qop.register(readout)

    with exp.acquire_loop_rt(
        uid="pulsed_twotone",
        count=settings.avg,
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
