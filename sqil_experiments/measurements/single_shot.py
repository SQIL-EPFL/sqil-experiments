# Copyright 2024 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0

"""This module defines the IQ_blob experiment.

In this experiment, we perform single-shot measurements with the qubits prepared
in the states g, e, and/or f.

The IQ blob experiment has the following pulse sequence:

    qb --- [ prepare transition ] --- [ measure ]

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from laboneq import serializers, workflow
from laboneq.simple import AveragingMode, Experiment, SectionAlignment, dsl
from laboneq_applications.analysis.iq_blobs import analysis_workflow
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

if TYPE_CHECKING:
    from collections.abc import Sequence

    from laboneq.dsl.quantum.qpu import QPU
    from laboneq_applications.typing import QuantumElements


@workflow.task_options(base_class=BaseExperimentOptions)
class SingleShotOptions:
    averaging_mode: AveragingMode = workflow.option_field(
        AveragingMode.SINGLE_SHOT, description="Averaging mode used for the experiment"
    )


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    initial_states: Sequence[str],
    options: SingleShotOptions | None = None,
) -> Experiment:
    """Creates an IQ-blob Experiment.

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubit to run the experiments on.
        states:
            The basis states the qubits should be prepared in. May be either a string,
            e.g. "gef", or a list of letters, e.g. ["g","e","f"].
        options:
            The options for building the experiment as an instance of
            [IQBlobExperimentOptions]. See the docstring of this class for more details.

    Returns:
        experiment:
            The generated LabOne Q experiment instance to be compiled and executed.
    """
    # Define the custom options for the experiment
    opts = SingleShotOptions() if options is None else options
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
        # with dsl.section(
        #     name="State preparation",
        #     alignment=SectionAlignment.RIGHT,
        # ):
        #     for q in qubits:
        #         for s0 in initial_states:
        #             qop.prepare_state.omit_section(q, s0)

        # with dsl.section(name="Measure", alignment=SectionAlignment.LEFT):
        #     for q in qubits:
        #         for s0 in initial_states:
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


class SingleShot(ExperimentHandler):
    exp_name = "single_shot"
    db_schema = {
        "g": {"role": "data", "unit": "V", "scale": 1e3},
        "e": {"role": "data", "unit": "V", "scale": 1e3},
        "initial_states": {"role": "param"},
    }

    def __init__(self, setup_path="", emulation=False, server=False, is_zi_exp=None):
        super().__init__(setup_path, emulation, server, is_zi_exp)
        self.save_zi_result = True

    def sequence(
        self,
        initial_states,
        qu_ids=["q0"],
        options: SingleShotOptions | None = None,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(self.qpu, qubits, initial_states, options=options)

    def analyze(self, path, *args, **kwargs):
        # exp_result = serializers.load(f"{path}/zi_result.json")
        # res = analysis_workflow(exp_result, self.qpu.quantum_elements, ["g", "e"]).run()
        # return res
        return analyze_single_shot(path=path, **kwargs)


@multi_qubit_handler
def analyze_single_shot(
    datadict, qpu=None, qu_id="q0", transition="ge", relevant_params=None, **kwargs
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    x_data, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    g = datadict["g"]
    e = datadict["e"]

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Set plot style
    set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        anal_res.add_figure(fig, "fig", qu_id)
        ax.scatter(np.real(g), np.imag(g), alpha=0.1)
        ax.scatter(np.real(e), np.imag(e), alpha=0.1)
        ax.grid(True)
        ax.set_aspect("equal")

    finalize_plot(
        fig,
        f"Single shot ({transition})",
        qu_id,
        fit_res,
        qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
