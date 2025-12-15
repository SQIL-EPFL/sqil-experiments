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

from sqil_experiments.measurements.T1 import analyze_T1

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
    options: TuneupExperimentOptions | None = None,
) -> Experiment:
    """Creates a lifetime_measurement Experiment.

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on. May be either a single
            qubit or a list of qubits.
        delays:
            The delays to sweep over for each qubit. If `qubits` is a
            single qubit, `amplitudes` must be a list of numbers or an array. Otherwise
            it must be a list of lists of numbers or arrays.
        options:
            The options for building the experiment.
            See [TuneupExperimentOptions] and [BaseExperimentOptions] for
            accepted options.
            Overwrites the options from [TuneupExperimentOptions] and
            [BaseExperimentOptions].

    Returns:
        experiment:
            The generated LabOne Q experiment instance to be compiled and executed.

    Raises:
        ValueError:
            If the qubits and qubit_delays are not of the same length.

        ValueError:
            If qubit_delays is not a list of numbers when a single qubit is passed.

        ValueError:
            If qubit_delays is not a list of lists of numbers.

        ValueError:
            If the experiment uses calibration traces and the averaging mode is
            sequential.

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
            delays=[[10e-9, 50e-9, 1], [10e-9, 50e-9, 1]],
            options=options,
        )
        ```
    """
    # Define the custom options for the experiment
    opts = TuneupExperimentOptions() if options is None else options
    qubits, delays = validation.validate_and_convert_qubits_sweeps(qubits, delays)
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
            with dsl.section(name="main", alignment=SectionAlignment.RIGHT):
                with dsl.section(
                    name="main_drive",
                    alignment=SectionAlignment.RIGHT,
                ):
                    for q, delay in zip(qubits, delays_sweep_pars):
                        qop.prepare_state.omit_section(q, opts.transition[0])

                        qop.aux_drive(q)
                        sec = qop.passive_reset(q, aux=True)
                        sec = qop.x180(q, transition="hdawg")

                        sec.alignment = SectionAlignment.RIGHT
                        qop.delay(q, time=delay)
                        qop.x180(q, transition="ge")
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


class T1_hdawg(ExperimentHandler):
    exp_name = "T1_hdawg"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "time": {"role": "x-axis", "unit": "s", "scale": 1e6},
    }

    def sequence(self, time, qu_ids=0, options=None, *args, **kwargs):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(self.qpu, qubits, time, options=options)

    def analyze(self, path, *args, **kwargs):
        return analyze_T1(path=path, **kwargs)
