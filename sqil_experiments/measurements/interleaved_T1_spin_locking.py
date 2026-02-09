"""This module defines the spin locking experiment.

The spin locking experiment has the following pulse sequence:

    qb --- [ prep transition ] --- [ x90_transition ] --- [ ry(delay) ] ---
    --- [ x90_transition ] --- [ measure ]

If multiple qubits are passed to the `run` workflow, the above pulses are applied
in parallel on all the qubits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import matplotlib.pyplot as plt
import numpy as np
import sqil_core.fit as fit
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.simple import Experiment, SectionAlignment, SweepParameter, dsl
from laboneq.workflow import option_field
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import TuneupExperimentOptions
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

from sqil_experiments.measurements.spin_locking import SpinLockingOptions

if TYPE_CHECKING:
    from laboneq.dsl.quantum.qpu import QPU
    from laboneq_applications.typing import QuantumElements, QubitSweepPoints


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    delays_T1: QubitSweepPoints,
    lengths_spin_locking: QubitSweepPoints,
    rel_amp: float | None = None,
    options: SpinLockingOptions | None = None,
    transition="ge",
    use_helper_drive=False,
) -> Experiment:
    """Creates a interleaved Spin echo Experiment.

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on. May be either a single
            qubit or a list of qubits.
        lengths:
            The delays to sweep over for each qubit. Note that `delays` must be
            identical for qubits that use the same measure port.
        rel_amp:
            The relative amplitude specifies the spin_locking pulse amplitude
            relative to the pi-pulse amplitude. Default is None and corresponds to
            the pi pulse amplitude of the specified transition.
        options:
            The options for building the experiment.
            See [EchoExperimentOptions] and [BaseExperimentOptions] for
            accepted options.
            Overwrites the options from [TuneupExperimentOptions] and
            [BaseExperimentOptions].

    Returns:
        experiment:
            The generated LabOne Q experiment instance to be compiled and executed.

    Raises:
        ValueError:
            If delays is not a list of numbers or array when a single qubit is passed.

    Example:
        ```python
        options = {
            "count": 10,
            "transition": "ge",
            "averaging_mode": "cyclic",
            "acquisition_type": "integration_trigger",
            "cal_traces": True,
        }
        options = TuneupExperimentOptions(**options)
        setup = DeviceSetup()
        qpu = QPU(
            setup=DeviceSetup("my_device"),
            qubits=[TunableTransmonQubit("q0"), TunableTransmonQubit("q1")],
            quantum_operations=TunableTransmonOperations(),
        )
        temp_qubits = qpu.copy_qubits()
        create_experiment(
            qpu=qpu,
            qubits=temp_qubits,
            lengths=[[1e-6, 5e-6, 10e-6], [1e-6, 5e-6, 10e-6]]
            options=options,
        )
        ```
    """
    # Define the custom options for the experiment
    opts = SpinLockingOptions() if options is None else options
    qubits, delays_T1 = validation.validate_and_convert_qubits_sweeps(qubits, delays_T1)
    angle = rel_amp * np.pi if rel_amp is not None else np.pi

    opts.transition = transition

    max_measure_section_length = qpu.measure_section_length(qubits)

    qop = qpu.quantum_operations
    with dsl.acquire_loop_rt(
        count=opts.count,
        averaging_mode=opts.averaging_mode,
        acquisition_type=opts.acquisition_type,
        repetition_mode=opts.repetition_mode,
        repetition_time=opts.repetition_time,
        reset_oscillator_phase=opts.reset_oscillator_phase,
    ):

        delays_sweep_pars = [
            SweepParameter(f"delays_{q.uid}", q_delays, axis_name=f"{q.uid}")
            for q, q_delays in zip(qubits, delays_T1)
        ]

        locking_length_sweep_pars = [
            SweepParameter(f"length_{q.uid}", q_lengths, axis_name=f"{q.uid}")
            for q, q_lengths in zip(qubits, lengths_spin_locking)
        ]

        with dsl.sweep(
            name="lifetime_measurement_sweep",
            parameter=delays_sweep_pars,
        ):
            if opts.active_reset:
                qop.active_reset(
                    qubits,
                    active_reset_states=opts.active_reset_states,
                    number_resets=opts.active_reset_repetitions,
                    measure_section_length=max_measure_section_length,
                )
            with dsl.section(name="T1", alignment=SectionAlignment.RIGHT):
                with dsl.section(
                    name="T1_drive",
                    alignment=SectionAlignment.RIGHT,
                ):
                    for q, delay in zip(qubits, delays_sweep_pars):
                        qop.prepare_state.omit_section(q, opts.transition[0])
                        sec = qop.x180(q, transition=opts.transition)
                        sec.alignment = SectionAlignment.RIGHT
                        qop.delay(q, time=delay)
                with dsl.section(name="T1_measure", alignment=SectionAlignment.LEFT):
                    for q in qubits:
                        sec = qop.measure(
                            q, dsl.handles.result_handle(f"{q.uid}/data_T1")
                        )
                        # Fix the length of the measure section
                        sec.length = max_measure_section_length
                        qop.passive_reset(q)

        with dsl.sweep(
            name="spin_locking_sweep",
            parameter=locking_length_sweep_pars,
        ):

            with dsl.section(name="spin_locking", alignment=SectionAlignment.RIGHT):

                with dsl.section(
                    name="spin_locking_seq",
                    alignment=SectionAlignment.RIGHT,
                ):
                    for q, length in zip(qubits, locking_length_sweep_pars):
                        qop.prepare_state(q, opts.transition[0])
                        qop.x90(q, opts.transition)
                        qop.ry(
                            q,
                            angle=angle,
                            transition=(
                                "helper" if use_helper_drive else opts.transition
                            ),
                            length=length,
                            # pulse=opts.pulse,
                        )
                        qop.x90(q, opts.transition)
                with dsl.section(
                    name="spin_locking_measure", alignment=SectionAlignment.LEFT
                ):
                    for q in qubits:
                        sec = qop.measure(
                            q, dsl.handles.result_handle(f"{q.uid}/data_spin_locking")
                        )
                        # Fix the length of the measure section
                        sec.length = max_measure_section_length
                        qop.passive_reset(q)


class InterleavedT1SpinLocking(ExperimentHandler):
    exp_name = "interleaved_T1_spin_locking"
    db_schema = {
        "data_T1": {"role": "data", "unit": "V", "scale": 1e3},
        "data_spin_locking": {"role": "data", "unit": "V", "scale": 1e3},
        "delays_T1": {"role": "x-axis", "unit": "s", "scale": 1e6},
        "lengths_spin_locking": {"role": "x-axis", "unit": "s", "scale": 1e6},
    }

    def sequence(
        self,
        delays_T1,
        lengths_spin_locking,
        qu_ids=["q0"],
        transition="ge",
        use_helper_drive=False,
        options: SpinLockingOptions | None = None,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(
            self.qpu,
            qubits,
            delays_T1,
            lengths_spin_locking,
            transition=transition,
            use_helper_drive=use_helper_drive,
            options=options,
        )

    def analyze(self, path, *args, **kwargs):
        return analyze_spin_echo(path=path, **kwargs)


@multi_qubit_handler
def analyze_spin_echo(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    fit_kwargs=None,
    **kwargs,
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    if fit_kwargs is None:
        fit_kwargs = {}

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    lengths, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    # Set plot style
    set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        try:
            # Project the data and start plot
            proj, inv = fit.transform_data(y_data, inv_transform=True)
            fig, axs = plot_projection_IQ(datadict=datadict, proj_data=proj)
            anal_res.add_figure(fig, "fig", qu_id)

            # Analyze
            fit_res = fit.fit_decaying_exp(lengths, proj, **fit_kwargs)

            anal_res.add_fit(fit_res, "Decaying oscillations", qu_id)
            # Update parameters
            anal_res.add_params(
                {f"decay": fit_res.params_by_name["tau"]},
                qu_id,
            )

            x_fit = np.linspace(lengths[0], lengths[-1], 10 * len(lengths))
            inverse_fit = inv(fit_res.predict(x_fit))

            # Plot the fit
            axs[0].plot(
                x_fit * x_info.scale,
                fit_res.predict(x_fit) * y_info.scale,
                "tab:red",
                alpha=0.8,
                linewidth=2,
            )
            axs[1].plot(
                inverse_fit.real * y_info.scale,
                inverse_fit.imag * y_info.scale,
                "tab:red",
            )

        except Exception as e:
            print("Error while fitting projected data", e)

    elif has_sweeps:
        # fig, axs = plot_mag_phase(datadict=datadict, raw=True)
        # anal_res.add_figure(fig, "fig", qu_id)

        spin_locking_amplitudes = sweeps[0]
        delays_T1 = datadict["delays_T1"]
        lengths_spin_locking = datadict["lengths_spin_locking"]
        proj_T1 = fit.transform_data(datadict["data_T1"])
        proj_spin_locking = fit.transform_data(datadict["data_spin_locking"])

        delays_T1, lengths_spin_locking, proj_T1, proj_spin_locking = (
            np.atleast_2d(delays_T1),
            np.atleast_2d(lengths_spin_locking),
            np.atleast_2d(proj_T1),
            np.atleast_2d(proj_spin_locking),
        )

        T1s, TSLs = (
            np.zeros(len(proj_T1)),
            np.zeros(len(proj_spin_locking)),
        )

        for i in range(len(spin_locking_amplitudes)):
            fit_res_T1, fit_res_TSL = None, None
            (
                delays_T1_itr,
                lengths_spin_locking_itr,
                proj_T1_itr,
                proj_spin_locking_itr,
            ) = (
                delays_T1[i],
                lengths_spin_locking[i],
                proj_T1[i],
                proj_spin_locking[i],
            )

            # Analyze T1
            try:
                fit_res_T1 = fit.fit_decaying_exp(
                    delays_T1_itr, proj_T1_itr, **fit_kwargs
                )
            except Exception as e:
                print(f"Error ananlyzing T1 trace {i}", e)
            if fit_res_T1 is not None:
                # fit_res_T1.summary()
                anal_res.add_fit(fit_res_T1, f"{i} - T1", qu_id)
                T1s[i] = fit_res_T1.params_by_name["tau"]

            # Analyze spin locking
            #################
            fig_itr, ax_itr = plt.subplots()
            ax_itr.scatter(lengths_spin_locking_itr * 1e9, proj_spin_locking_itr)
            #################

            try:
                fit_res_spin_locking = fit.fit_decaying_exp(
                    lengths_spin_locking_itr, proj_spin_locking_itr, **fit_kwargs
                )
            except Exception as e:
                print(f"Error ananlyzing spin locking trace {i}", e)
            if fit_res_spin_locking is not None:
                # fit_res_spin_locking.summary()

                x_fit = np.linspace(
                    lengths_spin_locking_itr[0],
                    lengths_spin_locking_itr[-1],
                    10 * len(lengths_spin_locking_itr),
                )
                # Plot the fit
                ax_itr.plot(
                    x_fit * 1e9,
                    fit_res_spin_locking.predict(x_fit),
                    "tab:red",
                    alpha=0.8,
                    linewidth=2,
                )

                rabi_freq = (
                    sweeps[0][i]
                    / qpu.quantum_elements[0].parameters.ge_drive_amplitude_pi
                ) / (qpu.quantum_elements[0].parameters.ge_drive_length * 2)

                ax_itr.set_title(
                    r"$Amplitude = $"
                    + "{:.4f}".format(sweeps[0][i])
                    + " V | "
                    + r"$\Omega_R = $"
                    + "{:.3f}".format(rabi_freq / 1e6)
                    + " MHz | "
                    + r"$\tau = $"
                    + "{:.6f}".format(fit_res_spin_locking.params_by_name["tau"])
                    + " s"
                )

                ax_itr.set_xlabel("pulse length [ns]")
                ax_itr.set_ylabel("Projected [mV]")

                anal_res.add_fit(fit_res_spin_locking, f"{i} - spinlocking", qu_id)
                TSLs[i] = fit_res_spin_locking.params_by_name["tau"]

        T1s_valid = np.where(T1s > 0, T1s, np.nan)
        TSLs_valid = np.where(TSLs > 0, TSLs, np.nan)

        T1, TSL = np.nanmean(T1s_valid), np.nanmean(TSLs_valid)

        # Plot
        T1_info = ParamInfo(f"{transition}_T1")
        T1_scaled = T1s_valid * T1_info.scale

        TSL_scale = (
            1e6  # TODO implement parameter infos for TSL spin locking time constant
        )
        TSLs_scaled = TSLs_valid * TSL_scale

        T1_info = ParamInfo(f"{transition}_T1")

        sweep_scaled = sweeps[0] * sweep_info[0].scale

        fig, axs = plt.subplots(3, 1, figsize=(22, 12), sharex=True)
        anal_res.add_figure(fig, "fig", qu_id)

        axs[0].plot(sweep_scaled, T1_scaled, ".-")
        axs[0].axhline(y=T1 * T1_info.scale, color="tab:pink", linestyle="--")
        axs[0].set_ylabel(T1_info.name_and_unit)

        axs[1].plot(sweep_scaled, TSLs_scaled, ".-")
        axs[1].axhline(y=TSL * TSL_scale, color="tab:pink", linestyle="--")
        axs[1].set_ylabel(r"$T_{SL} \ [\mu s]$")

        axs[2].plot(
            sweep_scaled,
            (1 / (TSLs) - 1 / (2 * T1s)),
            ".-",
        )
        axs[2].set_ylabel(r"$S_\omega (\Omega_R) \ [Hz]$")

        axs[2].set_xlabel("amplitde (spin-lock drive) [V]")
        axs[2].set_xscale("log")

        sweep_freq = (
            sweeps[0] / qpu.quantum_elements[0].parameters.ge_drive_amplitude_pi
        ) / (qpu.quantum_elements[0].parameters.ge_drive_length * 2)

        fig, axs = plt.subplots(3, 1, figsize=(22, 12), sharex=True)
        anal_res.add_figure(fig, "fig", qu_id)

        axs[0].plot(sweep_freq / 1e6, T1_scaled, ".-")
        axs[0].axhline(y=T1 * T1_info.scale, color="tab:pink", linestyle="--")
        axs[0].set_ylabel(T1_info.name_and_unit)

        axs[1].plot(sweep_freq / 1e6, TSLs_scaled, ".-")
        axs[1].axhline(y=TSL * TSL_scale, color="tab:pink", linestyle="--")
        axs[1].set_ylabel(r"$T_{SL} \ [\mu s]$")

        axs[2].plot(
            sweep_freq / 1e6,
            (1 / (TSLs_valid) - 1 / (2 * T1s_valid)),
            ".-",
        )
        axs[2].set_ylabel(r"$S_\omega (\Omega_R) \ [Hz]$")

        axs[2].set_xlabel("spin-lock rabi freq [MHz]")
        axs[2].set_yscale("log")

        axs[2].set_xscale("log")

    finalize_plot(
        fig,
        f"Spin locking spectroscopy",
        qu_id,
        fit_res,
        qubit_params,
        anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
