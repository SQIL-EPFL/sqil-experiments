from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import sqil_core.fit as fit
from laboneq.dsl.enums import AveragingMode
from laboneq.dsl.quantum import QPU
from laboneq.simple import Experiment, SectionAlignment, SweepParameter, dsl
from laboneq_applications.analysis.ramsey import validate_and_convert_detunings
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import TuneupExperimentOptions
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

if TYPE_CHECKING:
    from collections.abc import Sequence

    from laboneq.dsl.quantum.qpu import QPU
    from laboneq_applications.typing import QuantumElements, QubitSweepPoints


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    delays: QubitSweepPoints,
    detunings: float | Sequence[float] | None = None,
    options: TuneupExperimentOptions | None = None,
) -> Experiment:
    # Define the custom options for the experiment
    opts = TuneupExperimentOptions() if options is None else options
    qubits, delays = validation.validate_and_convert_qubits_sweeps(qubits, delays)
    detunings = validate_and_convert_detunings(qubits, detunings)
    if (
        opts.use_cal_traces
        and AveragingMode(opts.averaging_mode) == AveragingMode.SEQUENTIAL
    ):
        raise ValueError(
            "'AveragingMode.SEQUENTIAL' (or {AveragingMode.SEQUENTIAL}) cannot be used "
            "with calibration traces because the calibration traces are added "
            "outside the sweep."
        )

    swp_delays = []
    swp_phases = []
    for i, q in enumerate(qubits):
        q_delays = delays[i]
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
            with dsl.section(name="main", alignment=SectionAlignment.RIGHT):
                with dsl.section(name="main_drive", alignment=SectionAlignment.RIGHT):
                    for q, wait_time, phase in zip(qubits, swp_delays, swp_phases):
                        qop.prepare_state.omit_section(q, opts.transition[0])
                        qop.ramsey.omit_section(
                            q, wait_time, phase, transition=opts.transition
                        )
                with dsl.section(name="main_measure", alignment=SectionAlignment.LEFT):
                    for q in qubits:
                        sec = qop.measure(q, dsl.handles.result_handle(q.uid))
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


class Ramsey(ExperimentHandler):
    exp_name = "ramsey"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "time": {"role": "x-axis", "unit": "s", "scale": 1e6},
    }

    def sequence(self, time, detuning, qu_ids=["q0"], options=None, *args, **kwargs):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(self.qpu, qubits, time, detuning, options=options)

    def analyze(self, path, *args, **kwargs):
        return analyze_ramsey(path=path, **kwargs)


@multi_qubit_handler
def analyze_ramsey(
    datadict, qpu=None, qu_id="q0", transition="ge", relevant_params=None, **kwargs
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    x_data, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Set plot style
    set_plot_style(plt)

    # Plot raw data and extract projection
    fig, axs, proj, inv = plot_projection_IQ(datadict=datadict, full_output=True)
    anal_res.add_figure(fig, "fig", qu_id)

    # Try to fit the sum of 1, 2 and 3 decaying oscillations and see which one fits best
    best_fit = None
    n_oscillation = [1, 2, 3]
    for n in n_oscillation:
        try:
            fit_res = fit.fit_many_decaying_oscillations(x_data, proj, n)
        except:
            fit_res = None
        if fit_res is not None:
            anal_res.add_fit(fit_res, f"{n} oscillations", qu_id)
            if best_fit is None:
                best_fit = fit_res
                continue
            best_fit = fit.get_best_fit(best_fit, fit_res, recipe="nrmse_aic")

    if best_fit is not None:
        # Update parameters
        taus = [
            best_fit.params_by_name.get(f"tau{n}", np.inf)
            for n in range(len(n_oscillation))
        ]
        T2_star = np.min(taus)
        anal_res.add_params({f"{transition}_T2_star": T2_star}, qu_id)

        x_fit = np.linspace(x_data[0], x_data[-1], 3 * len(x_data))
        inverse_fit = inv(best_fit.predict(x_fit))

        # Plot the fit
        axs[0].plot(
            x_fit * x_info.scale, best_fit.predict(x_fit) * y_info.scale, "tab:red"
        )
        axs[1].plot(
            inverse_fit.real * y_info.scale,
            inverse_fit.imag * y_info.scale,
            "tab:red",
        )

    # Plot FFT
    x_fft, y_fft = compute_fft(x_data, proj)
    x_peaks, y_peaks = get_peaks(x_fft, y_fft)
    set_plot_style(plt)
    fig2, ax2 = plt.subplots(1, 1)
    ax2.plot(x_fft / 1e6, y_fft)
    ax2.scatter(
        x_peaks / 1e6,
        y_peaks,
        color="tab:red",
        marker="x",
        zorder=3,
        s=100,
        label="Peaks",
    )
    ax2.set_xlabel("Frequency [MHz]")
    ax2.set_ylabel("FFT amplitude")
    ax2.set_title("Fourier transform")
    ax2.legend()
    fig2.tight_layout()
    anal_res.add_figure(fig2, "fft", qu_id)

    finalize_plot(
        fig,
        f"Ramsey ({transition})",
        qu_id,
        best_fit,
        qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
