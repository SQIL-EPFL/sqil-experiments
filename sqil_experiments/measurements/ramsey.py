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
from sqil_core.experiment import AnalysisResult, ExperimentHandler
from sqil_core.utils import *

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
    detunings: float | Sequence[float] | None = None,
    options: TuneupExperimentOptions | None = None,
) -> Experiment:
    """Creates a Ramsey Experiment.

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on. May be either a single
            qubit or a list of qubits.
        delays:
            The delays (in seconds) of the second x90 pulse to sweep over for each
            qubit. If `qubits` is a single qubit, `delays` must be a list of numbers
            or an array. Otherwise, it must be a list of lists of numbers or arrays.
        detunings:
            The detuning in Hz introduced in order to generate oscillations of the qubit
            state vector around the Bloch sphere. This detuning and the frequency of the
            fitted oscillations is used to calculate the true qubit resonance frequency.
            `detunings` is a list of float values for each qubit following the order
            in `qubits`.
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
            If the lengths of `qubits` and `delays` do not match.

        ValueError:
            If `delays` is not a list of numbers when a single qubit is passed.

        ValueError:
            If `delays` is not a list of lists of numbers when a list of qubits
            is passed.

        ValueError:
            If the experiment uses calibration traces and the averaging mode is
            sequential.

    Example:
        ```python
        options = TuneupExperimentOptions()
        qpu = QPU(
            qubits=[TunableTransmonQubit("q0"), TunableTransmonQubit("q1")],
            quantum_operations=TunableTransmonOperations(),
        )
        temp_qubits = qpu.copy_qubits()
        create_experiment(
            qpu=qpu,
            qubits=temp_qubits,
            delays=[
                np.linspace(0, 20e-6, 51),
                np.linspace(0, 30e-6, 52),
            ],
            detunings = [1e6, 1.346e6],
            options=options,
        )
        ```
    """
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

    def sequence(self, time, detuning, qu_idx=0, options=None, *args, **kwargs):
        return create_experiment(
            self.qpu, self.qpu.quantum_elements[qu_idx], time, detuning, options=options
        )

    def analyze(
        self,
        path,
        datadict=None,
        qpu=None,
        qu_uid="q0",
        transition="ge",
        relevant_params=None,
        **kwargs,
    ):
        return analyze_ramsey(
            path=path,
            datadict=datadict,
            qpu=qpu,
            qu_uid=qu_uid,
            transition=transition,
            relevant_params=relevant_params,
        )


def analyze_ramsey(
    path=None,
    datadict=None,
    qpu=None,
    transition="ge",
    qu_uid="q0",
    relevant_params=None,
):
    # Extract data and metadata
    all_data, all_info, datadict = get_data_and_info(path=path, datadict=datadict)
    x_data, y_data, sweeps = all_data
    x_info, y_info, sweep_info = all_info

    # Extract qubit parameters
    if qpu is None and path is not None:
        qpu = read_qpu(path, "qpu_old.json")
    qubit_params = {}
    if qpu is not None:
        qubit_params = enrich_qubit_params(qpu.quantum_element_by_uid(qu_uid))

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Define analysis result
    anal_res = AnalysisResult()
    anal_res.updated_params[qu_uid] = {}
    fit_res = None

    # Plot raw data and extract projection
    fig, axs, proj, inv = sqil.plot_projection_IQ(datadict=datadict, full_output=True)
    anal_res.figures.update({"fig": fig})

    # Fit exponential
    fit_res = sqil.fit.fit_decaying_oscillations(x_data, proj)
    x_fit = np.linspace(x_data[0], x_data[-1], 3 * len(x_data))
    inverse_fit = inv(fit_res.predict(x_fit))

    # Update parameters
    T2_star = fit_res.params_by_name["tau"]
    anal_res.updated_params[qu_uid].update({f"{transition}_T2_star": T2_star})

    # Plot the fit
    axs[0].plot(x_fit * x_info.scale, fit_res.predict(x_fit) * y_info.scale, "tab:red")
    axs[1].plot(
        inverse_fit.real * y_info.scale,
        inverse_fit.imag * y_info.scale,
        "tab:red",
    )

    finalize_plot(
        fig,
        f"Ramsey ({transition})",
        fit_res,
        qubit_params,
        updated_params=anal_res.updated_params[qu_uid],
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
