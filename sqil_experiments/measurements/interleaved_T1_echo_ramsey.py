from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from laboneq.simple import Experiment, SectionAlignment, SweepParameter, dsl
from laboneq.workflow import option_field, task_options
from laboneq_applications.analysis.ramsey import validate_and_convert_detunings
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import (
    BaseExperimentOptions,
    TuneupExperimentOptions,
)
from matplotlib.gridspec import GridSpec
from numpy.typing import ArrayLike
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

from sqil_experiments.measurements.T2_echo import EchoExperimentOptions

if TYPE_CHECKING:
    from collections.abc import Sequence

    from laboneq.dsl.quantum import TransmonParameters
    from laboneq.dsl.quantum.qpu import QPU
    from laboneq.dsl.session import Session
    from laboneq_applications.typing import QuantumElements, QubitSweepPoints


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    delays: QubitSweepPoints,
    delays_ramsey: QubitSweepPoints,
    detunings: float | Sequence[float] | None = None,
    options: EchoExperimentOptions | None = None,
) -> Experiment:
    # Define the custom options for the experiment
    opts = EchoExperimentOptions() if options is None else options
    qubits, delays_T1 = validation.validate_and_convert_qubits_sweeps(qubits, delays)

    if (
        opts.use_cal_traces
        and AveragingMode(opts.averaging_mode) == AveragingMode.SEQUENTIAL
    ):
        raise ValueError(
            "'AveragingMode.SEQUENTIAL' (or {AveragingMode.SEQUENTIAL}) cannot be used "
            "with calibration traces because the calibration traces are added "
            "outside the sweep."
        )

    delays_sweep_pars = [
        SweepParameter(f"delays_{q.uid}", q_delays, axis_name=f"{q.uid}")
        for q, q_delays in zip(qubits, delays)
    ]

    ### opts = TuneupExperimentOptions() if options is None else options
    #### qubits, delays = validation.validate_and_convert_qubits_sweeps(qubits, delays)
    _, delays_ramsey = validation.validate_and_convert_qubits_sweeps(
        qubits, delays_ramsey
    )
    detunings = validate_and_convert_detunings(qubits, detunings)

    swp_delays = []
    swp_phases = []
    for i, q in enumerate(qubits):
        q_delays = delays_ramsey[i]
        swp_delays += [
            SweepParameter(
                uid=f"wait_time_{q.uid}",
                values=q_delays,
            ),
        ]
        swp_phases += [
            SweepParameter(
                uid=f"x90_phases_{q.uid}",
                values=np.array(
                    [
                        ((wait_time - q_delays[0]) * detunings[i] * 2 * np.pi)
                        % (2 * np.pi)
                        for wait_time in q_delays
                    ]
                ),
            ),
        ]

    ###

    # We will fix the length of the measure section to the longest section among
    # the qubits to allow the qubits to have different readout and/or
    # integration lengths.
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
        if opts.use_cal_traces:
            qop.calibration_traces.omit_section(
                qubits=qubits,
                states=opts.cal_states,
                active_reset=opts.active_reset,
                active_reset_states=opts.active_reset_states,
                active_reset_repetitions=opts.active_reset_repetitions,
                measure_section_length=max_measure_section_length,
            )

        with dsl.sweep(
            name="echo_sweep",
            parameter=delays_sweep_pars,
        ):
            if opts.active_reset:
                qop.active_reset(
                    qubits,
                    active_reset_states=opts.active_reset_states,
                    number_resets=opts.active_reset_repetitions,
                    measure_section_length=max_measure_section_length,
                )
            with dsl.section(name="echo", alignment=SectionAlignment.RIGHT):
                with dsl.section(name="echo_drive", alignment=SectionAlignment.RIGHT):
                    for q, delay in zip(qubits, delays_sweep_pars):
                        qop.prepare_state.omit_section(q, opts.transition[0])
                        qop.ramsey(
                            q,
                            delay,
                            0,
                            echo_pulse=opts.refocus_qop,
                            transition=opts.transition,
                        )
                with dsl.section(name="echo_measure", alignment=SectionAlignment.LEFT):
                    for q in qubits:
                        sec = qop.measure(
                            q, dsl.handles.result_handle(f"{q.uid}/data_echo")
                        )
                        # Fix the length of the measure section
                        sec.length = max_measure_section_length
                        qop.passive_reset(q)
        if opts.use_cal_traces:
            qop.calibration_traces.omit_section(
                qubits=qubits,
                states=opts.cal_states,
                active_reset=opts.active_reset,
                active_reset_states=opts.active_reset_states,
                active_reset_repetitions=opts.active_reset_repetitions,
                measure_section_length=max_measure_section_length,
            )

        with dsl.sweep(
            name="ramsey_sweep",
            parameter=swp_delays + swp_phases,
        ):
            if opts.active_reset:
                qop.active_reset(
                    qubits,
                    active_reset_states=opts.active_reset_states,
                    number_resets=opts.active_reset_repetitions,
                    measure_section_length=max_measure_section_length,
                )
            with dsl.section(name="ramsey", alignment=SectionAlignment.RIGHT):
                with dsl.section(name="ramsey_drive", alignment=SectionAlignment.RIGHT):
                    for q, wait_time, phase in zip(qubits, swp_delays, swp_phases):
                        qop.prepare_state.omit_section(q, opts.transition[0])
                        qop.ramsey.omit_section(
                            q, wait_time, phase, transition=opts.transition
                        )
                with dsl.section(
                    name="ramsey_measure", alignment=SectionAlignment.LEFT
                ):
                    for q in qubits:
                        sec = qop.measure(
                            q, dsl.handles.result_handle(f"{q.uid}/data_ramsey")
                        )
                        # Fix the length of the measure section
                        sec.length = max_measure_section_length
                        qop.passive_reset(q)
        if opts.use_cal_traces:
            qop.calibration_traces.omit_section(
                qubits=qubits,
                states=opts.cal_states,
                active_reset=opts.active_reset,
                active_reset_states=opts.active_reset_states,
                active_reset_repetitions=opts.active_reset_repetitions,
                measure_section_length=max_measure_section_length,
            )


class InterleavedT1EchoRamsey(ExperimentHandler):
    exp_name = "Interleaved T1-Echo-Ramsey"
    db_schema = {
        "data_T1": {"role": "data", "unit": "V", "scale": 1e3},
        "data_echo": {"role": "data", "unit": "V", "scale": 1e3},
        "data_ramsey": {"role": "data", "unit": "V", "scale": 1e3},
        "time": {"role": "x-axis", "unit": "s", "scale": 1e6},
        "time_ramsey": {"role": "x-axis", "unit": "s", "scale": 1e6},
    }

    def sequence(
        self, time, time_ramsey, detuning, qu_ids=["q0"], options=None, *args, **kwargs
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(
            self.qpu, qubits, time, time_ramsey, detuning, options=options
        )

    def analyze(self, path, *args, **kwargs):
        return analyze_interleaved_T1_echo_ramsey(path=path, **kwargs)


@multi_qubit_handler
def analyze_interleaved_T1_echo_ramsey(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    outlier_threshold=3.5,
    **kwargs,
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    *_, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Set plot style
    sqil.set_plot_style(plt)

    times = datadict["time"]
    times_ramsey = datadict["time_ramsey"]
    proj_T1 = sqil.fit.transform_data(datadict["data_T1"])
    proj_echo = sqil.fit.transform_data(datadict["data_echo"])
    proj_ramsey = sqil.fit.transform_data(datadict["data_ramsey"])

    times, times_ramsey, proj_T1, proj_echo, proj_ramsey = (
        np.atleast_2d(times),
        np.atleast_2d(times_ramsey),
        np.atleast_2d(proj_T1),
        np.atleast_2d(proj_echo),
        np.atleast_2d(proj_ramsey),
    )

    T1s, T2s, T2stars, T2stars_freq = (
        np.zeros(len(proj_T1)),
        np.zeros(len(proj_echo)),
        np.zeros(len(proj_ramsey)),
        np.zeros((len(proj_ramsey), 3)),
    )
    for i in range(len(times)):
        fit_res_T1, fit_res_echo, fit_res_ramsey = None, None, None
        time, time_ramsey, data_T1, data_echo, data_ramsey = (
            times[i],
            times_ramsey[i],
            proj_T1[i],
            proj_echo[i],
            proj_ramsey[i],
        )

        # Analyze T1
        try:
            fit_res_T1 = sqil.fit.fit_decaying_exp(time, data_T1)
        except Exception as e:
            print(f"Error ananlyzing T1 trace {i}", e)
        if fit_res_T1 is not None:
            anal_res.add_fit(fit_res_T1, f"{i} - T1", qu_id)
            T1s[i] = fit_res_T1.params_by_name["tau"]

        # Analyze echo
        try:
            fit_res_echo = sqil.fit.fit_decaying_exp(time, data_echo)
        except Exception as e:
            print(f"Error ananlyzing echo trace {i}", e)
        if fit_res_echo is not None:
            anal_res.add_fit(fit_res_echo, f"{i} - echo", qu_id)
            T2s[i] = fit_res_echo.params_by_name["tau"]

        # Try to fit the sum of 1, 2 and 3 decaying oscillations and see which one fits best
        best_fit = None
        n_oscillation = [1, 2, 3]

        for n in n_oscillation:
            try:
                fit_res = sqil.fit.fit_many_decaying_oscillations(
                    time_ramsey, data_ramsey, n
                )
            except:
                fit_res = None
            if fit_res is not None:
                anal_res.add_fit(fit_res, f"{n} oscillations", qu_id)
                if best_fit is None:
                    best_fit = fit_res
                    continue
                best_fit = sqil.fit.get_best_fit(best_fit, fit_res, recipe="nrmse_aic")

        if best_fit is not None:
            fit_res = best_fit
            # Update parameters
            taus = [
                best_fit.params_by_name.get(f"tau{n}", np.inf)
                for n in range(len(n_oscillation))
            ]
            T2stars[i] = np.min(taus)
            T2stars_freq[i] = [
                best_fit.params_by_name.get(f"T{n}", np.nan)
                for n in range(len(n_oscillation))
            ]

    T1s_valid = np.where(T1s > 0, T1s, np.nan)
    T1s_masked = mask_outliers(T1s_valid, outlier_threshold)
    T2s_valid = np.where(T2s > 0, T2s, np.nan)
    T2s_masked = mask_outliers(T2s_valid, outlier_threshold)
    T2stars_valid = np.where(T2stars > 0, T2stars, np.nan)
    T2stars_masked = mask_outliers(T2stars_valid, outlier_threshold)

    T1s_mask_inv = np.isnan(T1s_masked) & ~np.isnan(T1s_valid)
    T1s_outliers = np.full_like(T1s_valid, np.nan)
    T1s_outliers[T1s_mask_inv] = T1s_valid[T1s_mask_inv]

    T2s_mask_inv = np.isnan(T2s_masked) & ~np.isnan(T2s_valid)
    T2s_outliers = np.full_like(T2s_valid, np.nan)
    T2s_outliers[T2s_mask_inv] = T2s_valid[T2s_mask_inv]

    T2stars_mask_inv = np.isnan(T2stars_masked) & ~np.isnan(T2stars_valid)
    T2stars_outliers = np.full_like(T2stars_valid, np.nan)
    T2stars_outliers[T2stars_mask_inv] = T2stars_valid[T2stars_mask_inv]

    # Update parameters
    T1, T2, T2star = (
        np.nanmean(T1s_masked),
        np.nanmean(T2s_masked),
        np.nanmean(T2stars_masked),
    )

    anal_res.add_params(
        {
            f"{transition}_T1": T1,
            f"{transition}_T2": T2,
            f"{transition}_T2_star": T2star,
        },
        qu_id,
    )
    if transition == "ge":
        anal_res.add_params({"reset_delay_length": 5.01 * T1}, qu_id)

    # Plot
    T1_info = ParamInfo(f"{transition}_T1")
    echo_info = ParamInfo(f"{transition}_T2")
    ramsey_info = ParamInfo(f"{transition}_T2_star")

    T1_scaled = T1s_masked * T1_info.scale
    echo_scaled = T2s_masked * echo_info.scale
    ramsey_scaled = T2stars_masked * ramsey_info.scale

    T1_outliers_scaled = T1s_outliers * T1_info.scale
    echo_outliers_scaled = T2s_outliers * echo_info.scale
    ramsey_outliers_scaled = T2stars_outliers * ramsey_info.scale

    if len(proj_T1) == 1:
        sweeps = np.array([[1]])
        sweep_info = [ParamInfo("index")]
    sweep_scaled = sweeps[0] * sweep_info[0].scale

    fig, axs = plt.subplots(3, 1, figsize=(32, 12))
    anal_res.add_figure(fig, "fig", qu_id)

    axs[0].plot(sweep_scaled, T1_scaled, ".-")
    axs[0].plot(sweep_scaled, T1_outliers_scaled, ".-", color="red", alpha=0.5)
    axs[0].axhline(y=T1 * T1_info.scale, color="tab:pink", linestyle="--")
    axs[0].set_ylabel(T1_info.name_and_unit)

    axs[1].plot(sweep_scaled, echo_scaled, ".-")
    axs[1].plot(sweep_scaled, echo_outliers_scaled, ".-", color="red", alpha=0.5)
    axs[1].axhline(y=T2 * echo_info.scale, color="tab:pink", linestyle="--")
    axs[1].set_ylabel(echo_info.name_and_unit)

    axs[2].plot(sweep_scaled, ramsey_scaled, ".-")
    axs[2].plot(sweep_scaled, ramsey_outliers_scaled, ".-", color="red", alpha=0.5)
    axs[2].axhline(y=T2star * ramsey_info.scale, color="tab:pink", linestyle="--")
    axs[2].set_ylabel(ramsey_info.name_and_unit)

    finalize_plot(
        fig,
        f"Interleaved T1-echo-ramsey ({transition})",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res


@multi_qubit_handler
def analyze_interleaved_T1_echo_ramsey_beating_checks(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    outlier_threshold=3.5,
    **kwargs,
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    *_, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Set plot style
    sqil.set_plot_style(plt)

    times = datadict["time"]
    times_ramsey = datadict["time_ramsey"]
    proj_T1 = sqil.fit.transform_data(datadict["data_T1"])
    proj_echo = sqil.fit.transform_data(datadict["data_echo"])
    proj_ramsey = sqil.fit.transform_data(datadict["data_ramsey"])

    times, times_ramsey, proj_T1, proj_echo, proj_ramsey = (
        np.atleast_2d(times),
        np.atleast_2d(times_ramsey),
        np.atleast_2d(proj_T1),
        np.atleast_2d(proj_echo),
        np.atleast_2d(proj_ramsey),
    )

    T1s, T2s, T2stars, T2stars_freq = (
        np.zeros(len(proj_T1)),
        np.zeros(len(proj_echo)),
        np.zeros(len(proj_ramsey)),
        np.zeros((len(proj_ramsey), 3)),
    )
    for i in range(len(times)):
        fit_res_T1, fit_res_echo, fit_res_ramsey = None, None, None
        time, time_ramsey, data_T1, data_echo, data_ramsey = (
            times[i],
            times_ramsey[i],
            proj_T1[i],
            proj_echo[i],
            proj_ramsey[i],
        )

        # Analyze T1
        try:
            fit_res_T1 = sqil.fit.fit_decaying_exp(time, data_T1)
        except Exception as e:
            print(f"Error ananlyzing T1 trace {i}", e)
        if fit_res_T1 is not None:
            anal_res.add_fit(fit_res_T1, f"{i} - T1", qu_id)
            T1s[i] = fit_res_T1.params_by_name["tau"]

        # Analyze echo
        try:
            fit_res_echo = sqil.fit.fit_decaying_exp(time, data_echo)
        except Exception as e:
            print(f"Error ananlyzing echo trace {i}", e)
        if fit_res_echo is not None:
            anal_res.add_fit(fit_res_echo, f"{i} - echo", qu_id)
            T2s[i] = fit_res_echo.params_by_name["tau"]

        # Try to fit the sum of 1, 2 and 3 decaying oscillations and see which one fits best
        best_fit = None
        n_oscillation = [1, 2, 3]

        for n in n_oscillation:
            try:
                fit_res = sqil.fit.fit_many_decaying_oscillations(
                    time_ramsey, data_ramsey, n
                )
            except:
                fit_res = None
            if fit_res is not None:
                anal_res.add_fit(fit_res, f"{n} oscillations", qu_id)
                if best_fit is None:
                    best_fit = fit_res
                    continue
                best_fit = sqil.fit.get_best_fit(best_fit, fit_res, recipe="nrmse_aic")

        if best_fit is not None:
            fit_res = best_fit
            # Update parameters
            taus = [
                best_fit.params_by_name.get(f"tau{n}", np.inf)
                for n in range(len(n_oscillation))
            ]
            T2stars[i] = np.min(taus)
            T2stars_freq[i] = [
                best_fit.params_by_name.get(f"T{n}", np.nan)
                for n in range(len(n_oscillation))
            ]

    T2stars_single_exp, T2stars_errors = (
        np.zeros(len(proj_ramsey)),
        np.zeros(len(proj_ramsey)),
    )
    for i in range(len(times)):
        fit_res_T1, fit_res_echo, fit_res_ramsey = None, None, None
        time_ramsey, data_ramsey = (
            times_ramsey[i],
            proj_ramsey[i],
        )

        # Try to fit the sum of 1, 2 and 3 decaying oscillations and see which one fits best
        best_fit = None
        n_oscillation = [1]

        for n in n_oscillation:
            try:
                fit_res = sqil.fit.fit_many_decaying_oscillations(
                    time_ramsey, data_ramsey, n
                )
            except:
                fit_res = None
            if fit_res is not None:
                anal_res.add_fit(fit_res, f"{n} oscillations", qu_id)
                if best_fit is None:
                    best_fit = fit_res
                    continue
                best_fit = sqil.fit.get_best_fit(best_fit, fit_res, recipe="nrmse_aic")

        if best_fit is not None:
            fit_res = best_fit
            # Update parameters
            taus = [
                best_fit.params_by_name.get(f"tau{n}", np.inf)
                for n in range(len(n_oscillation))
            ]
            T2stars_single_exp[i] = np.min(taus)
            T2stars_errors[i] = best_fit.metrics["nrmse"]

    T2stars_valid = np.where(T2stars > 0, T2stars, np.nan)
    T2stars_masked = mask_outliers(T2stars_valid, outlier_threshold)
    T2stars_mask_inv = np.isnan(T2stars_masked) & ~np.isnan(T2stars_valid)
    T2stars_outliers = np.full_like(T2stars_valid, np.nan)
    T2stars_outliers[T2stars_mask_inv] = T2stars_valid[T2stars_mask_inv]

    fig_beating_check, axs_beating_check = plt.subplots(3, 1, figsize=(32, 12))
    anal_res.add_figure(fig_beating_check, "fig", qu_id)

    if len(proj_T1) == 1:
        sweeps = np.array([[1]])
        sweep_info = [ParamInfo("index")]
    sweep_scaled = sweeps[0] * sweep_info[0].scale

    # Plot
    ramsey_info = ParamInfo(f"{transition}_T2_star")
    ramsey_scaled = T2stars_single_exp * ramsey_info.scale
    ramsey_outliers_scaled = T2stars_outliers * ramsey_info.scale

    axs_beating_check[0].plot(sweep_scaled, ramsey_scaled, ".-")
    axs_beating_check[0].set_ylabel(ramsey_info.name_and_unit + " | single osc")

    axs_beating_check[1].plot(sweep_scaled, T2stars_errors, ".-")
    axs_beating_check[1].set_ylabel("nrmse" + " | single osc")

    nan_counts = np.isnan(T2stars_freq).sum(axis=1)
    T2stars_freq_n1 = np.where(nan_counts[:, None] == 2, T2stars_freq, np.nan)
    T2stars_freq_n2 = np.where(nan_counts[:, None] == 1, T2stars_freq, np.nan)
    T2stars_freq_n3 = np.where(nan_counts[:, None] == 0, T2stars_freq, np.nan)

    axs_beating_check[2].scatter(
        sweep_scaled, T2stars_freq_n1[:, 0] / 1e6, label="1 osc", color="tab:blue"
    )
    axs_beating_check[2].scatter(
        sweep_scaled, T2stars_freq_n2[:, 0] / 1e6, label="2 osc", color="tab:orange"
    )
    axs_beating_check[2].scatter(
        sweep_scaled, T2stars_freq_n2[:, 1] / 1e6, color="tab:orange"
    )
    axs_beating_check[2].scatter(
        sweep_scaled, T2stars_freq_n3[:, 0] / 1e6, label="3 osc", color="tab:red"
    )
    axs_beating_check[2].scatter(
        sweep_scaled, T2stars_freq_n3[:, 1] / 1e6, color="tab:red"
    )
    axs_beating_check[2].scatter(
        sweep_scaled, T2stars_freq_n3[:, 2] / 1e6, color="tab:red"
    )
    axs_beating_check[2].legend()
    axs_beating_check[2].set_ylabel("fitted osc [MHz]")

    finalize_plot(
        fig_beating_check,
        f"Interleaved T1-echo-ramsey ({transition}) | ramsey beating checks",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=None,
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res


@multi_qubit_handler
def analyze_interleaved_T1_echo_ramsey_freq_fit_ramsey(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    outlier_threshold=3.5,
    **kwargs,
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    *_, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Set plot style
    sqil.set_plot_style(plt)

    times = datadict["time"]
    times_ramsey = datadict["time_ramsey"]
    proj_T1 = sqil.fit.transform_data(datadict["data_T1"])
    proj_echo = sqil.fit.transform_data(datadict["data_echo"])
    proj_ramsey = sqil.fit.transform_data(datadict["data_ramsey"])

    times, times_ramsey, proj_T1, proj_echo, proj_ramsey = (
        np.atleast_2d(times),
        np.atleast_2d(times_ramsey),
        np.atleast_2d(proj_T1),
        np.atleast_2d(proj_echo),
        np.atleast_2d(proj_ramsey),
    )

    n_oscillation = [1, 2]

    T1s, T2s, T2stars, T2stars_freq = (
        np.zeros(len(proj_T1)),
        np.zeros(len(proj_echo)),
        np.zeros(len(proj_ramsey)),
        np.zeros((len(proj_ramsey), len(n_oscillation))),
    )
    for i in range(len(times)):
        fit_res_T1, fit_res_echo, fit_res_ramsey = None, None, None
        time, time_ramsey, data_T1, data_echo, data_ramsey = (
            times[i],
            times_ramsey[i],
            proj_T1[i],
            proj_echo[i],
            proj_ramsey[i],
        )

        # Analyze T1
        try:
            fit_res_T1 = sqil.fit.fit_decaying_exp(time, data_T1)
        except Exception as e:
            print(f"Error ananlyzing T1 trace {i}", e)
        if fit_res_T1 is not None:
            anal_res.add_fit(fit_res_T1, f"{i} - T1", qu_id)
            T1s[i] = fit_res_T1.params_by_name["tau"]

        # Analyze echo
        try:
            fit_res_echo = sqil.fit.fit_decaying_exp(time, data_echo)
        except Exception as e:
            print(f"Error ananlyzing echo trace {i}", e)
        if fit_res_echo is not None:
            anal_res.add_fit(fit_res_echo, f"{i} - echo", qu_id)
            T2s[i] = fit_res_echo.params_by_name["tau"]

        # Try to fit the sum of 1, 2 and 3 decaying oscillations and see which one fits best
        best_fit = None

        for n in n_oscillation:
            try:
                fit_res = sqil.fit.fit_many_decaying_oscillations(
                    time_ramsey, data_ramsey, n
                )
            except:
                fit_res = None
            if fit_res is not None:
                anal_res.add_fit(fit_res, f"{n} oscillations", qu_id)
                if best_fit is None:
                    best_fit = fit_res
                    continue
                best_fit = sqil.fit.get_best_fit(best_fit, fit_res, recipe="nrmse_aic")

        if best_fit is not None:
            fit_res = best_fit
            # Update parameters
            taus = [
                best_fit.params_by_name.get(f"tau{n}", np.inf)
                for n in range(len(n_oscillation))
            ]
            T2stars[i] = np.min(taus)
            T2stars_freq[i] = [
                best_fit.params_by_name.get(f"T{n}", np.nan)
                for n in range(len(n_oscillation))
            ]

    T2stars_single_exp, T2stars_errors = (
        np.zeros(len(proj_ramsey)),
        np.zeros(len(proj_ramsey)),
    )
    for i in range(len(times)):
        fit_res_T1, fit_res_echo, fit_res_ramsey = None, None, None
        time_ramsey, data_ramsey = (
            times_ramsey[i],
            proj_ramsey[i],
        )

        # Try to fit the sum of 1, 2 and 3 decaying oscillations and see which one fits best
        best_fit = None
        n_oscillation = [1]

        for n in n_oscillation:
            try:
                fit_res = sqil.fit.fit_many_decaying_oscillations(
                    time_ramsey, data_ramsey, n
                )
            except:
                fit_res = None
            if fit_res is not None:
                anal_res.add_fit(fit_res, f"{n} oscillations", qu_id)
                if best_fit is None:
                    best_fit = fit_res
                    continue
                best_fit = sqil.fit.get_best_fit(best_fit, fit_res, recipe="nrmse_aic")

        if best_fit is not None:
            fit_res = best_fit
            # Update parameters
            taus = [
                best_fit.params_by_name.get(f"tau{n}", np.inf)
                for n in range(len(n_oscillation))
            ]
            T2stars_single_exp[i] = np.min(taus)
            T2stars_errors[i] = best_fit.metrics["nrmse"]

    T2stars_valid = np.where(T2stars > 0, T2stars, np.nan)
    T2stars_masked = mask_outliers(T2stars_valid, outlier_threshold)
    T2stars_mask_inv = np.isnan(T2stars_masked) & ~np.isnan(T2stars_valid)
    T2stars_outliers = np.full_like(T2stars_valid, np.nan)
    T2stars_outliers[T2stars_mask_inv] = T2stars_valid[T2stars_mask_inv]

    fig_beating_check, axs_beating_check = plt.subplots(1, 1, figsize=(32, 5))
    anal_res.add_figure(fig_beating_check, "fig", qu_id)

    if len(proj_T1) == 1:
        sweeps = np.array([[1]])
        sweep_info = [ParamInfo("index")]
    sweep_scaled = sweeps[0] * sweep_info[0].scale

    # Plot
    ramsey_info = ParamInfo(f"{transition}_T2_star")
    ramsey_scaled = T2stars_single_exp * ramsey_info.scale
    ramsey_outliers_scaled = T2stars_outliers * ramsey_info.scale

    nan_counts = np.isnan(T2stars_freq).sum(axis=1)
    T2stars_freq_n1 = np.where(nan_counts[:, None] == 1, T2stars_freq, np.nan)
    T2stars_freq_n2 = np.where(nan_counts[:, None] == 0, T2stars_freq, np.nan)

    axs_beating_check.scatter(
        sweep_scaled, T2stars_freq_n1[:, 0] / 1e6, label="1 osc", color="tab:blue"
    )
    axs_beating_check.scatter(
        sweep_scaled, T2stars_freq_n2[:, 0] / 1e6, label="2 osc", color="tab:orange"
    )
    axs_beating_check.scatter(
        sweep_scaled, T2stars_freq_n2[:, 1] / 1e6, color="tab:orange"
    )

    axs_beating_check.legend()
    axs_beating_check.set_ylabel("fitted osc [MHz]")

    finalize_plot(
        fig_beating_check,
        f"Interleaved T1-echo-ramsey ({transition}) | ramsey beating checks",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=None,
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
