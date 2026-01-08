# Copyright 2024 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0

"""This module defines the qubit spectroscopy experiment.

In this experiment, we sweep the frequency of a qubit drive pulse to characterize
the qubit transition frequency.

The qubit spectroscopy experiment has the following pulse sequence:

    qb --- [ prep transition ] --- [ x180_transition (swept frequency)] --- [ measure ]

If multiple qubits are passed to the `run` workflow, the above pulses are applied
in parallel on all the qubits.
"""

import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from laboneq import workflow
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.dsl.quantum.qpu import QPU
from laboneq.simple import Experiment, SectionAlignment, SweepParameter, dsl
from laboneq.workflow import option_field, task_options
from laboneq_applications.core.validation import validate_and_convert_qubits_sweeps
from laboneq_applications.experiments.options import BaseExperimentOptions
from laboneq_applications.typing import QuantumElements, QubitSweepPoints
from sqil_core.experiment import ExperimentHandler


@task_options(base_class=BaseExperimentOptions)
class QuSpecOptions:
    spectroscopy_reset_delay: float = option_field(
        1e-6, description="How long to wait after an acquisition in seconds."
    )
    acquisition_type: AcquisitionType = option_field(
        AcquisitionType.SPECTROSCOPY,
        description="Acquisition type to use for the experiment.",
    )
    averaging_mode: str | AveragingMode = option_field(
        AveragingMode.CYCLIC,
        description="Averaging mode to use for the experiment.",
        converter=AveragingMode,
    )


# @workflow.task
@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    frequencies: QubitSweepPoints,
    transition: str = "ge",
    options: QuSpecOptions | None = None,
) -> Experiment:
    # Define the custom options for the experiment
    opts = QuSpecOptions() if options is None else options

    qubits, frequencies = validate_and_convert_qubits_sweeps(qubits, frequencies)

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
        for q, q_frequencies in zip(qubits, frequencies):
            with dsl.sweep(
                name=f"freqs_{q.uid}",
                parameter=SweepParameter(f"frequency_{q.uid}", q_frequencies),
            ) as frequency:
                qop.prepare_state.omit_section(q, state=transition[0])
                with dsl.section(name="drive", alignment=SectionAlignment.RIGHT):
                    qop.set_frequency(q, frequency, transition=transition)
                    qop.qubit_spectroscopy_drive(q, transition=transition)
                    sec = qop.measure(q, dsl.handles.result_handle(q.uid))
                    # we fix the length of the measure section to the longest section among
                    # the qubits to allow the qubits to have different readout and/or
                    # integration lengths.
                    sec.length = max_measure_section_length
                    qop.passive_reset(q, delay=opts.spectroscopy_reset_delay)


class QuSpec(ExperimentHandler):
    exp_name = "qubit_spectroscopy"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "frequencies": {"role": "x-axis", "unit": "Hz", "scale": 1e-9},
    }

    def sequence(
        self,
        frequencies,
        transition="ge",
        qu_ids=["q0"],
        options: QuSpecOptions | None = None,
        *params,
        **kwargs,
    ):
        qu_ids = make_iterable(qu_ids)
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        if np.array(frequencies).ndim == 1:
            frequencies = [frequencies]
        return create_experiment(
            self.qpu, qubits, frequencies, options=options, transition=transition
        )

    def analyze(self, path, *args, **kwargs):
        return qu_spec_analysis(path=path, **kwargs)


from sqil_core.experiment import AnalysisResult, multi_qubit_handler
from sqil_core.fit import FitQuality
from sqil_core.utils import *

from sqil_experiments.analysis.fit import find_shared_peak

# map_data_dict, extract_h5_data, param_info_from_schema, enrich_qubit_params, get_relevant_exp_parameters, plot_mag_phase, ONE_TONE_PARAMS, ParamInfo


@multi_qubit_handler
def qu_spec_analysis(
    datadict,
    qu_id="q0",
    transition="ge",
    qpu=None,
    at_sweep_idx=None,
    relevant_params=["spectroscopy_amplitude"],
    **kwargs,
) -> AnalysisResult:
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    x_data, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res = None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    # Set plot style
    sqil.set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        # Plot without fit
        fig, axs = plot_mag_phase(datadict=datadict)
        anal_res.add_figure(fig, "fig", qu_id)

        # Fit data to extract parameters
        try:
            is_wide_range = x_data[-1] - x_data[0] > 200e6
            mag, phase = np.abs(y_data), np.unwrap(np.angle(y_data))
            fit_res, trace = find_shared_peak(x_data, mag, phase, full_output=True)
        except Exception as e:
            print(f"Error while fitting", e)
        if fit_res is not None:
            # Save fit result and extract parameters
            anal_res.add_fit(fit_res, "Combined mag-phase fit", qu_id)
            param_id = f"resonance_frequency_{transition}"
            anal_res.add_params({param_id: fit_res.params_by_name["x0"]}, qu_id)
            # Plot
            x_fit = np.linspace(x_data[0], x_data[-1], np.max([2000, len(x_data)]))
            if trace in ["mag", "phase"]:
                ax_idx = 1
                y_fit_scaled = fit_res.predict(x_fit)
                if trace == "mag":
                    ax_idx = 0
                    y_fit_scaled *= y_info.scale
                axs[ax_idx].plot(x_fit * x_info.scale, y_fit_scaled, color="tab:red")
            elif trace == "both":
                y_fit = fit_res.predict(x_fit, x_fit, *fit_res.params)
                y_fit_mag = y_fit[: len(x_fit)] * y_info.scale
                y_fit_phase = y_fit[len(x_fit) :]
                axs[0].plot(x_fit * x_info.scale, y_fit_mag, color="tab:red")
                axs[1].plot(x_fit * x_info.scale, y_fit_phase, color="tab:red")
    else:
        invert_sweep_axis = False
        if sweep_info[0].id == "current":
            invert_sweep_axis = True
        fig, axs = plot_mag_phase(datadict=datadict, transpose=invert_sweep_axis)
        anal_res.add_figure(fig, "fig", qu_id)
        fit_res = None

    finalize_plot(
        fig,
        f"Qubit spectroscopy ({transition})",
        qu_id,
        fit_res,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )
    fig.tight_layout()

    return anal_res
