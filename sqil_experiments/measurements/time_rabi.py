import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from laboneq.simple import (
    Experiment,
    SectionAlignment,
    SweepParameter,
    dsl,
    pulse_library,
)
from laboneq.workflow import option_field, task_options
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from matplotlib.gridspec import GridSpec
from numpy.typing import ArrayLike
from sqil_core.experiment import ExperimentHandler


@task_options(base_class=BaseExperimentOptions)
class TimeRabiOptions:
    """Options for the time Rabi experiment."""

    transition: str = option_field("ge", description="Transition to apply pulse.")
    acquisition_type: AcquisitionType = option_field(
        AcquisitionType.INTEGRATION, description="Acquisition type."
    )
    averaging_mode: str | AveragingMode = option_field(
        AveragingMode.CYCLIC,
        description="Averaging mode.",
        converter=AveragingMode,
    )
    transition: str = option_field("ge", description="Transition, ge or ef")


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubit: QuantumElement,
    pulse_lengths: ArrayLike,
    options: TimeRabiOptions | None = None,
) -> Experiment:
    opts = TimeRabiOptions() if options is None else options
    qubit, pulse_lengths = validation.validate_and_convert_single_qubit_sweeps(
        qubit, pulse_lengths
    )
    qop = qpu.quantum_operations

    sweep_param = SweepParameter(
        uid=f"pulse_length_{qubit.uid}",
        values=pulse_lengths,
        axis_name="Pulse length [s]",
    )

    with dsl.acquire_loop_rt(
        count=opts.count,
        averaging_mode=opts.averaging_mode,
        acquisition_type=opts.acquisition_type,
        repetition_mode=opts.repetition_mode,
        repetition_time=opts.repetition_time,
        reset_oscillator_phase=opts.reset_oscillator_phase,
    ):
        with dsl.sweep(name="time_rabi_sweep", parameter=sweep_param) as pulse_len:
            with dsl.section(name="drive", alignment=SectionAlignment.RIGHT):
                qop.prepare_state.omit_section(qubit, state=opts.transition[0])
                qop.x180(
                    q=qubit,
                    length=pulse_len + 20e-9,
                    pulse={"can_compress": True, "width": pulse_len},
                    transition="ge",
                )
            with dsl.section(name="measure", alignment=SectionAlignment.LEFT):
                qop.measure(qubit, dsl.handles.result_handle(qubit.uid))
                qop.passive_reset(qubit)


from sqil_core.experiment import AnalysisResult


class TimeRabi(ExperimentHandler):
    exp_name = "time_rabi"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "pulse_lengths": {"role": "x-axis", "unit": "s", "scale": 1e9},
    }

    def sequence(
        self,
        pulse_lengths,
        qu_idx=0,
        options: TimeRabiOptions | None = None,
        *params,
        **kwargs,
    ):
        return create_experiment(
            self.qpu,
            self.qpu.qubits[qu_idx],
            pulse_lengths,
            options=options,
        )

    def analyze(
        self, path, qu_uid="q0", transition="ge", relevant_params=None, **kwargs
    ):
        # FIXME: passing qu_uid = qu_uid causes an error, unhashable type: 'numpy.ndarray'
        return analyze_time_rabi(
            path=path,
            qu_uid="q0",
            transition=transition,
            relevant_params=relevant_params,
            **kwargs,
        )


from sqil_core.utils import *


def analyze_time_rabi(
    path=None,
    datadict=None,
    qpu=None,
    qu_uid="q0",
    transition="ge",
    relevant_params=None,
    **kwargs,
):
    # Extract data and metadata
    all_data, all_info, datadict = get_data_and_info(path=path, datadict=datadict)
    lengths, y_data, sweeps = all_data
    x_info, y_info, sweep_info = all_info

    # Extract qubit parameters
    if qpu is None and path is not None:
        qpu = read_qpu(path, "qpu_old.json")
    qubit_params = {}
    if qpu is not None:
        qubit_params = enrich_qubit_params(qpu.quantum_element_by_uid(qu_uid))

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    anal_res = AnalysisResult()
    anal_res.updated_params[qu_uid] = {}
    fit_res = None

    sqil.set_plot_style(plt)

    has_sweeps = y_data.ndim > 1

    if not has_sweeps:
        try:
            # Project the data and start plot
            proj, inv = sqil.fit.transform_data(y_data, inv_transform=True)
            fig, axs = plot_projection_IQ(datadict=datadict, proj_data=proj)
            anal_res.figures.update({"fig": fig})
            # Analyze
            fit_res_exp = sqil.fit.fit_decaying_oscillations(lengths, proj)
            fit_res_const = sqil.fit.fit_oscillations(lengths, proj)
            fit_res = sqil.fit.get_best_fit(
                fit_res_exp, fit_res_const, recipe="nrmse_aic"
            )

            anal_res.fits.update({"Decaying oscillations": fit_res_exp})
            anal_res.fits.update({"Constant oscillations": fit_res_const})
            # Update parameters
            anal_res.updated_params[qu_uid].update(
                {f"{transition}_drive_length": fit_res.metadata["pi_time"]}
            )

            x_fit = np.linspace(lengths[0], lengths[-1], 3 * len(lengths))
            inverse_fit = inv(fit_res.predict(x_fit))

            # Make parameters pretty
            omega_r = sqil.format_number(1 / fit_res.params_by_name["T"], unit="Hz")
            t_pi = sqil.format_number(fit_res.metadata["pi_time"], unit="s")

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

    finalize_plot(
        fig,
        f"Time Rabi ({transition})",
        fit_res,
        qubit_params,
        anal_res.updated_params[qu_uid],
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
