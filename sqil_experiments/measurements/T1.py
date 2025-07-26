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
from sqil_core.experiment import AnalysisResult, ExperimentHandler
from sqil_core.utils import *

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
                        sec = qop.x180(q, transition=opts.transition)
                        sec.alignment = SectionAlignment.RIGHT
                        qop.delay(q, time=delay)
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


class T1(ExperimentHandler):
    exp_name = "T1"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "time": {"role": "x-axis", "unit": "s", "scale": 1e6},
    }

    def sequence(self, time, qu_idx=0, options=None, *args, **kwargs):
        return create_experiment(
            self.qpu, self.qpu.quantum_elements[qu_idx], time, options=options
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
        return analyze_T1(
            path=path,
            datadict=datadict,
            qpu=qpu,
            qu_uid=qu_uid,
            transition=transition,
            relevant_params=relevant_params,
            **kwargs,
        )


def analyze_T1(
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
    fit_res = sqil.fit.fit_decaying_exp(x_data, proj)
    x_fit = np.linspace(x_data[0], x_data[-1], 3 * len(x_data))
    inverse_fit = inv(fit_res.predict(x_fit))

    # Update parameters
    T1 = fit_res.params_by_name["tau"]
    anal_res.updated_params[qu_uid].update({f"{transition}_T1": T1})
    if transition == "ge":
        anal_res.updated_params[qu_uid].update({"reset_delay_length": 5.01 * T1})

    # Plot the fit
    axs[0].plot(x_fit * x_info.scale, fit_res.predict(x_fit) * y_info.scale, "tab:red")
    axs[1].plot(
        inverse_fit.real * y_info.scale,
        inverse_fit.imag * y_info.scale,
        "tab:red",
    )

    finalize_plot(
        fig,
        f"T1 ({transition})",
        fit_res,
        qubit_params,
        updated_params=anal_res.updated_params[qu_uid],
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
