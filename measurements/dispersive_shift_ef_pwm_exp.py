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
            ExperimentSignal("qu_drive_gf"),
        ],
    )

    # define the signal mapping between the LogicalSignals and the ExperimentSignals
    signal_map = {
        "measure": "/logical_signal_groups/q0/measure",
        "acquire": "/logical_signal_groups/q0/acquire",
        "qu_drive": "/logical_signal_groups/q0/shfqc_drive",
        "qu_drive_gf": "/logical_signal_groups/q0/shfqc_drive_ef",  # need to map the logical ef-drive to a gf-drive, to play a piece-wise-modulated ge-ef pair
    }
    exp.set_signal_map(signal_map)

    ################## Calibration (parameter setting) ##################

    # define an experiment calibration (set parameters)
    cal = Calibration()

    ###readout pulse#####################################################
    # define the readout pulse shape
    ro_pulse = pulse_library.const(
        uid="ro_pulse",
        length=param_dict["ro_pulse_length"],
        amplitude=1.0,  # should be 1.0 always
    )

    # define the qubit drive pulse length and shape
    ro_if_freq_sweep = LinearSweepParameter(
        uid="ro_if_freq_sweep",
        start=param_dict["ro_freq_start"] - param_dict["ro_lo_freq"],
        stop=param_dict["ro_freq_stop"] - param_dict["ro_lo_freq"],
        count=param_dict["ro_freq_npts"],
        axis_name="Readout if frequency [Hz]",
    )

    # define an readout if and lo frequency
    ro_if_oscillator = Oscillator(frequency=ro_if_freq_sweep)
    ro_lo_oscillator = Oscillator(frequency=param_dict["ro_lo_freq"])
    # add oscillators to ExperimentalSignal
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

    # define the qubit drive if and lo frequency
    # place IF + LO between the ge and ef frequencies
    if_osc_freq = (param_dict["qu_freq"] + param_dict["qu_ef_freq"]) / 2 - param_dict[
        "qu_lo_freq"
    ]
    qu_if_oscillator = Oscillator(
        frequency=if_osc_freq, modulation_type=ModulationType.HARDWARE
    )
    qu_lo_oscillator = Oscillator(
        frequency=param_dict["qu_lo_freq"], modulation_type=ModulationType.AUTO
    )
    # define oscillator
    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_drive_power"])
    cal["qu_drive"] = SignalCalibration(
        oscillator=qu_if_oscillator,
        local_oscillator=qu_lo_oscillator,
        range=qu_power_range,
    )

    # define the qubit drive pulse length and shape for piece-wise modulation
    # determine the pwm carrier frequency such that ge_freq = LO + IF + pwm_pulse_freq
    pwm_pulse_freq = (
        param_dict["qu_freq"] - (param_dict["qu_freq"] + param_dict["qu_ef_freq"]) / 2
    )
    pwm_pulse_amp = qu_signal_amp
    pwm_pulse_length = param_dict["qu_pi_pulse_length"]
    sampling_rate = 2e9
    oscillating_array = np.array(
        [
            np.exp(-1j * 2 * np.pi * pwm_pulse_freq * k / sampling_rate)
            for k in range(int(pwm_pulse_length * sampling_rate))
        ]
    )
    # define pulse shape
    target_pulse = pulse_library.cos2(
        uid="ge_pulse", length=pwm_pulse_length, amplitude=pwm_pulse_amp
    )
    timearray, env_array = target_pulse.generate_sampled_pulse()
    env_array = env_array.real  # envelope doesn't have imag
    # multiply the PWM carrier with the envelop of the target pulse
    pwm_array = env_array * oscillating_array
    qu_drive_pulse_pwm = pulse_library.sampled_pulse_complex(
        uid="cos_pwm_pulse", samples=pwm_array
    )
    qu_drive_pulse = qu_drive_pulse_pwm

    plt.figure()
    plt.title("pwm ge pulse")
    plt.plot(qu_drive_pulse.samples.real, label="pwm_real")
    plt.plot(qu_drive_pulse.samples.imag, label="pwm_imag")
    plt.xlabel("time [ns]")
    plt.ylabel("envelope [arb]")
    plt.legend()

    ###combined ge ef drive pair pulse##############################################################
    # define the qubit drive if and lo frequency
    # place IF + LO between the ge and ef frequencies
    if_osc_freq = (param_dict["qu_freq"] + param_dict["qu_ef_freq"]) / 2 - param_dict[
        "qu_lo_freq"
    ]
    print("IF_freq: " + str(if_osc_freq))
    qu_gf_if_oscillator = Oscillator(
        frequency=if_osc_freq, modulation_type=ModulationType.HARDWARE
    )
    qu_gf_lo_oscillator = Oscillator(
        frequency=param_dict["qu_lo_freq"], modulation_type=ModulationType.AUTO
    )
    # define oscillator
    qu_power_range, qu_signal_amp = shfqa_power_calculator(param_dict["qu_drive_power"])
    cal["qu_drive_gf"] = SignalCalibration(
        oscillator=qu_gf_if_oscillator,
        local_oscillator=qu_gf_lo_oscillator,
        range=qu_power_range,
    )

    sampling_rate = 2e9
    ge_pwm_pulse_freq = (
        param_dict["qu_freq"] - (param_dict["qu_freq"] + param_dict["qu_ef_freq"]) / 2
    )
    ge_pwm_pulse_length = param_dict["qu_pi_pulse_length"]
    ge_pwm_pulse_amp = qu_signal_amp

    ef_pwm_pulse_freq = (
        param_dict["qu_ef_freq"]
        - (param_dict["qu_freq"] + param_dict["qu_ef_freq"]) / 2
    )
    ef_pwm_pulse_length = param_dict["qu_ef_pi_pulse_length"]
    ef_pwm_pulse_amp = qu_signal_amp

    print("ge-PWM_freq: " + str(ge_pwm_pulse_freq))
    print("ge-PWM_freq: " + str(ef_pwm_pulse_freq))

    ge_pulse = pulse_library.cos2(
        uid="ge_pulse", length=ge_pwm_pulse_length, amplitude=ge_pwm_pulse_amp
    )

    ef_pulse = pulse_library.cos2(
        uid="ge_pulse", length=ef_pwm_pulse_length, amplitude=ef_pwm_pulse_amp
    )

    ge_timearray, ge_env_array = ge_pulse.generate_sampled_pulse()
    ge_env_array = env_array.real  # envelope doesn't have imag
    ge_oscillating_array = np.array(
        [
            np.exp(-1j * 2 * np.pi * ge_pwm_pulse_freq * k / sampling_rate)
            for k in range(int(ge_pwm_pulse_length * sampling_rate))
        ]
    )

    ge_pwm_array = ge_env_array * ge_oscillating_array
    ge_drive_pulse_pwm = pulse_library.sampled_pulse_complex(
        uid="cos_ge_pwm_pulse", samples=ge_pwm_array
    )

    ef_timearray, ef_env_array = ef_pulse.generate_sampled_pulse()
    ef_env_array = ef_env_array.real  # envelope doesn't have imag
    ef_oscillating_array = np.array(
        [
            np.exp(-1j * 2 * np.pi * ef_pwm_pulse_freq * k / sampling_rate)
            for k in range(int(ef_pwm_pulse_length * sampling_rate))
        ]
    )

    ef_pwm_array = ef_env_array * ef_oscillating_array
    ef_drive_pulse_pwm = pulse_library.sampled_pulse_complex(
        uid="cos_ef_pwm_pulse", samples=ef_pwm_array
    )

    # concatenate the ge and ef pulse
    qu_gf_drive_pulse_pwm = pulse_library.sampled_pulse_complex(
        uid="cos_gf_pwm_pulse",
        samples=np.concatenate(
            [ge_drive_pulse_pwm.samples, ef_drive_pulse_pwm.samples]
        ),
    )
    qu_gf_drive_pulse = qu_gf_drive_pulse_pwm

    plt.figure()
    plt.title("pwm gf pulse pair")
    plt.plot(qu_gf_drive_pulse_pwm.samples.real, label="pwm_real")
    plt.plot(qu_gf_drive_pulse_pwm.samples.imag, label="pwm_imag")
    plt.xlabel("time [ns]")
    plt.ylabel("envelope [arb]")
    plt.legend()

    # set the experiment calibration to the experiment instance
    exp.set_calibration(cal)

    #######################################################################################
    ## define experimental sequence
    # loop - average multiple measurements for each frequency - measurement in spectroscopy mode
    with exp.acquire_loop_rt(
        uid="dispersive_shift",
        count=param_dict["avg"],
        averaging_mode=AveragingMode.CYCLIC,
        acquisition_type=AcquisitionType.SPECTROSCOPY,
    ):
        # inner loop - real time sweep of readout frequency
        with exp.sweep(
            uid="ro_if_freq_sweep",
            parameter=ro_if_freq_sweep,
            alignment=SectionAlignment.RIGHT,
        ):
            # Qubit e-state cavity resonance
            with exp.section(
                uid="ge_excitation",
                on_system_grid=True,
            ):
                exp.play(
                    signal="qu_drive",
                    pulse=qu_drive_pulse,
                )
            with exp.section(
                uid="state_e_readout",
                play_after="ge_excitation",
                # alignment=SectionAlignment.LEFT,
            ):
                exp.measure(
                    measure_signal="measure",
                    measure_pulse=ro_pulse,
                    handle="e_state",
                    acquire_signal="acquire",
                    integration_length=param_dict["ro_pulse_length"],
                    reset_delay=param_dict["reset_delay"],
                )

            # Qubit f-state cavity resonance
            with exp.section(
                uid="gf_excitation",
                play_after="state_e_readout",
                alignment=SectionAlignment.RIGHT,
                trigger=None,
                on_system_grid=True,
            ):
                exp.play(
                    signal="qu_drive_gf",
                    pulse=qu_gf_drive_pulse,
                )

            # measurement
            with exp.section(
                uid="state_f_readout",
                play_after="gf_excitation",
                alignment=SectionAlignment.LEFT,
                on_system_grid=True,
            ):
                exp.measure(
                    measure_signal="measure",
                    measure_pulse=ro_pulse,
                    handle="f_state",
                    acquire_signal="acquire",
                    integration_length=param_dict["ro_pulse_length"],
                    reset_delay=param_dict["reset_delay"],
                )
    return exp
