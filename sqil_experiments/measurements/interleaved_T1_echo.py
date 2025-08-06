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
    from laboneq.dsl.quantum import TransmonParameters
    from laboneq.dsl.quantum.qpu import QPU
    from laboneq.dsl.session import Session
    from laboneq_applications.typing import QuantumElements, QubitSweepPoints


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    delays: QubitSweepPoints,
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


class InterleavedT1Echo(ExperimentHandler):
    exp_name = "Interleaved T1-Echo"
    db_schema = {
        "data_T1": {"role": "data", "unit": "V", "scale": 1e3},
        "data_echo": {"role": "data", "unit": "V", "scale": 1e3},
        "time": {"role": "x-axis", "unit": "s", "scale": 1e6},
    }

    def sequence(self, time, qu_ids=["q0"], options=None, *args, **kwargs):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(self.qpu, qubits, time, options=options)

    def analyze(self, path, *args, **kwargs):
        return analyze_interleaved_T1_echo(path=path, **kwargs)


@multi_qubit_handler
def analyze_interleaved_T1_echo(
    datadict, qpu=None, qu_id="q0", transition="ge", relevant_params=None, **kwargs
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
    proj_T1 = sqil.fit.transform_data(datadict["data_T1"])
    proj_echo = sqil.fit.transform_data(datadict["data_echo"])

    times, proj_T1, proj_echo = (
        np.atleast_2d(times),
        np.atleast_2d(proj_T1),
        np.atleast_2d(proj_echo),
    )

    T1s, T2s = np.zeros(len(proj_T1)), np.zeros(len(proj_echo))
    for i in range(len(times)):
        fit_res_T1, fit_res_echo = None, None
        time, data_T1, data_echo = times[i], proj_T1[i], proj_echo[i]

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

        # Update parameters
        T1, T2 = np.mean(T1s), np.mean(T2s)
        anal_res.add_params(
            {
                f"{transition}_T1": T1,
                f"{transition}_T2": T2,
            },
            qu_id,
        )
        if transition == "ge":
            anal_res.add_params({"reset_delay_length": 5.01 * T1}, qu_id)

    # Plot
    T1_info = ParamInfo(f"{transition}_T1")
    echo_info = ParamInfo(f"{transition}_T2")
    T1_scaled = T1s * T1_info.scale
    echo_scaled = T2s * echo_info.scale

    if len(proj_T1) == 1:
        sweeps = np.array([[1]])
        sweep_info = [ParamInfo("index")]
    sweep_scaled = sweeps[0] * sweep_info[0].scale

    fig, axs = plt.subplots(2, 1, figsize=(22, 12))
    anal_res.add_figure(fig, "fig", qu_id)

    axs[0].plot(sweep_scaled, T1_scaled, ".-")
    axs[0].axhline(y=T1 * T1_info.scale, color="tab:pink", linestyle="--")
    axs[0].set_ylabel(T1_info.name_and_unit)

    axs[1].plot(sweep_scaled, echo_scaled, ".-")
    axs[1].axhline(y=T2 * echo_info.scale, color="tab:pink", linestyle="--")
    axs[1].set_ylabel(echo_info.name_and_unit)

    finalize_plot(
        fig,
        f"Interleaved T1-echo ({transition})",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
