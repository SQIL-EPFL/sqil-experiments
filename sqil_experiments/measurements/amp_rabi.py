from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import sqil_core.fit as fit
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
from numpy.typing import ArrayLike
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

if TYPE_CHECKING:
    from laboneq_applications.typing import QuantumElements, QubitSweepPoints


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    amplitudes: QubitSweepPoints,
    options: TuneupExperimentOptions | None = None,
    transition="ge",
    operation_id="x180",
    N_pulses=1,
) -> Experiment:
    # Define the custom options for the experiment
    opts = TuneupExperimentOptions() if options is None else options
    opts.transition = transition
    qubits, amplitudes = validation.validate_and_convert_qubits_sweeps(
        qubits, amplitudes
    )

    amps_sweep_pars = [
        SweepParameter(f"amplitude_{q.uid}", q_amplitudes, axis_name=f"{q.uid}")
        for q, q_amplitudes in zip(qubits, amplitudes, strict=False)
    ]
    # We will fix the length of the measure section to the longest section among
    # the qubits to allow the qubits to have different readout and/or
    # integration lengths.
    max_measure_section_length = qpu.measure_section_length(qubits)
    qop = qpu.quantum_operations

    if hasattr(qop, operation_id):
        operation = getattr(qop, operation_id)
    else:
        raise AttributeError(
            f"{operation_id} is not a valid operation."
            " Check your QuantumOperations object."
        )

    with dsl.acquire_loop_rt(
        count=opts.count,
        averaging_mode=opts.averaging_mode,
        acquisition_type=opts.acquisition_type,
        repetition_mode=opts.repetition_mode,
        repetition_time=opts.repetition_time,
        reset_oscillator_phase=opts.reset_oscillator_phase,
    ):
        with dsl.sweep(
            name="rabi_amp_sweep",
            parameter=amps_sweep_pars,
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
                    for q, q_amplitudes in zip(qubits, amps_sweep_pars, strict=False):
                        qop.prepare_state.omit_section(q, state=opts.transition[0])
                        for _ in range(N_pulses):
                            sec = operation(
                                q, amplitude=q_amplitudes, transition=opts.transition
                            )
                            sec.alignment = SectionAlignment.RIGHT
                with dsl.section(name="main_measure", alignment=SectionAlignment.LEFT):
                    for q in qubits:
                        sec = qop.measure(q, dsl.handles.result_handle(q.uid))
                        # Fix the length of the measure section
                        sec.length = max_measure_section_length
                        qop.passive_reset(q)


class AmpRabi(ExperimentHandler):
    exp_name = "amp_rabi"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "amplitude": {"role": "x-axis", "unit": "", "scale": 1},
    }

    def sequence(
        self,
        amplitude,
        qu_ids=["q0"],
        transition="ge",
        options: TuneupExperimentOptions | None = None,
        N_pulses=1,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(
            self.qpu,
            qubits[0],
            amplitude[0],
            transition=transition,
            options=options,
            N_pulses=N_pulses,
        )

    def analyze(self, path, *args, **kwargs):
        return analyze_amp_rabi(path=path, **kwargs)


@multi_qubit_handler
def analyze_amp_rabi(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    operation_id="x180",
    N_pulses=1,
    **kwargs,
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    x_data, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    # Adjust for pulse train
    x_data *= N_pulses

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_length"]

    # Set plot style
    set_plot_style(plt)

    amp_name = "drive_amplitude_pi"
    if operation_id is not None and operation_id.endswith("90"):
        amp_name += "2"

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        try:
            # Project the data and start plot
            proj, inv = fit.transform_data(y_data, inv_transform=True)
            fig, axs = plot_projection_IQ(datadict=datadict, proj_data=proj)
            anal_res.add_figure(fig, "fig", qu_id)
            # Analyze
            fit_res_exp = fit.fit_decaying_oscillations(x_data, proj)
            fit_res_const = fit.fit_oscillations(x_data, proj)
            fit_res = fit.get_best_fit(fit_res_exp, fit_res_const, recipe="nrmse_aic")

            anal_res.add_fit(fit_res_exp, "Decaying oscillations", qu_id)
            anal_res.add_fit(fit_res_const, "Constant oscillations", qu_id)
            # Update parameters
            anal_res.add_params(
                {f"{transition}_{amp_name}": fit_res.metadata["pi_time"]}, qu_id
            )

            x_fit = np.linspace(x_data[0], x_data[-1], 3 * len(x_data))
            inverse_fit = inv(fit_res.predict(x_fit))

            # Plot the fit
            axs[0].plot(
                x_fit * x_info.scale, fit_res.predict(x_fit) * y_info.scale, "tab:red"
            )
            axs[1].plot(
                inverse_fit.real * y_info.scale,
                inverse_fit.imag * y_info.scale,
                "tab:red",
            )
        except Exception as e:
            print("Error while fitting projected data", e)

    elif has_sweeps:
        fig, axs = plot_mag_phase(datadict=datadict, raw=True)
        anal_res.add_figure(fig, "fig", qu_id)

    pulse_title = f"{N_pulses} {operation_id} pulse{'s' if N_pulses > 1 else ''}"
    finalize_plot(
        fig,
        f"Amp Rabi {pulse_title} ({transition})",
        qu_id,
        fit_res,
        qubit_params,
        anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
