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

from sqil_experiments.measurements.qu_spec import qu_spec_analysis


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
                with dsl.section(name="drive", alignment=SectionAlignment.RIGHT):
                    qop.prepare_state(q, state=transition[0])

                    # AUX pulse
                    qop.aux_drive(q)
                    qop.passive_reset(q, aux=True)

                    # HDAWG pulse
                    qop.set_frequency(q, frequency, transition="hdawg")
                    qop.hdawg_drive(q)

                    # qop.qubit_spectroscopy_drive(q, transition="ge")
                    qop.x180(q, transition="ge")
                    sec = qop.measure(q, dsl.handles.result_handle(q.uid))
                    # we fix the length of the measure section to the longest section among
                    # the qubits to allow the qubits to have different readout and/or
                    # integration lengths.
                    sec.length = max_measure_section_length
                    qop.passive_reset(q, delay=opts.spectroscopy_reset_delay)


class QuSpecHdawg(ExperimentHandler):
    exp_name = "qubit_spectroscopy_hdawg"
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
