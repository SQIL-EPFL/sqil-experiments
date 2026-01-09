from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from laboneq import workflow
from laboneq.simple import AveragingMode, Experiment, SectionAlignment, dsl
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

if TYPE_CHECKING:
    from collections.abc import Sequence

    from laboneq.dsl.quantum.qpu import QPU
    from laboneq_applications.typing import QuantumElements


@workflow.task_options(base_class=BaseExperimentOptions)
class IQBlobsOptions:
    averaging_mode: AveragingMode = workflow.option_field(
        AveragingMode.SINGLE_SHOT, description="Averaging mode used for the experiment"
    )


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    initial_states: Sequence[str],
    options: IQBlobsOptions | None = None,
) -> Experiment:
    # Define the custom options for the experiment
    opts = IQBlobsOptions() if options is None else options
    qubits = validation.validate_and_convert_qubits_sweeps(qubits)

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

        # Equivalent pulse sequence
        # for s0 in initial_states:
        #     with dsl.section(
        #         name="State preparation",
        #         alignment=SectionAlignment.RIGHT,
        #     ):
        #         for q in qubits:
        #             qop.prepare_state.omit_section(q, s0)

        #     with dsl.section(name="Measure", alignment=SectionAlignment.LEFT):
        #         for q in qubits:
        #             qop.measure(q, dsl.handles.result_handle(f"{q.uid}/{s0}"))
        #             qop.passive_reset(q)

        qop.calibration_traces.omit_section(
            qubits=qubits,
            states=initial_states,
            active_reset=opts.active_reset,
            active_reset_states=opts.active_reset_states,
            active_reset_repetitions=opts.active_reset_repetitions,
            measure_section_length=max_measure_section_length,
        )


class IQBlobs(ExperimentHandler):
    exp_name = "iq_blobs"
    db_schema = {}  # Dynamic schema computed before experiment

    def __init__(self, setup_path="", emulation=False, server=False, is_zi_exp=None):
        super().__init__(setup_path, emulation, server, is_zi_exp)
        self.save_zi_result = True

    def on_before_experiment(self, *args, **kwargs):
        self.db_schema = {
            "initial_states": {"role": "param"},
        }
        initial_states = self.run_args[0][0]
        for s in initial_states:
            self.db_schema.update({s: {"role": "data", "unit": "V", "scale": 1e3}})

    def sequence(
        self,
        initial_states,
        qu_ids=["q0"],
        options: IQBlobsOptions | None = None,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(self.qpu, qubits, initial_states, options=options)

    def analyze(self, path, *args, **kwargs):
        return analyze_iq_blobs(path=path, **kwargs)


@multi_qubit_handler
def analyze_iq_blobs(datadict, qpu=None, qu_id="q0", relevant_params=None, **kwargs):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    x_data, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    # Look at the entries in the db schema to extract the measured states
    db_schema_keys = list(datadict["metadata"]["schema"].keys())
    db_schema_keys.remove("initial_states")
    states = db_schema_keys

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        if "e" in states:
            relevant_params = [f"ge_drive_amplitude_pi"]
        if "f" in states:
            relevant_params = [f"ef_drive_amplitude_pi"]

    # Set plot style
    set_plot_style(plt)

    blob_colors = {"g": "tab:blue", "e": "tab:orange", "f": "tab:green"}
    edge_colors = {"g": "cyan", "e": "yellow", "f": "lime"}

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        anal_res.add_figure(fig, "fig", qu_id)

        for s in states:
            state = 1e3 * datadict.get(s, np.nan)
            ax.scatter(
                np.real(state),
                np.imag(state),
                alpha=0.1,
                color=blob_colors[s],
                zorder=-1,
            )
            plot_IQ_ellipse(state, ax, color=edge_colors[s], label=s, conf=0.99)

        ax.grid(True)
        ax.set_aspect("equal")
        ax.set_xlabel("In-phase [mV]")
        ax.set_ylabel("Quadrature [mV]")
        ax.legend()

    finalize_plot(
        fig,
        f"IQ blobs",
        qu_id,
        fit_res,
        qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
