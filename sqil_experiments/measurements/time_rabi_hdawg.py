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


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubit: QuantumElement,
    pulse_lengths: ArrayLike,
    options: TimeRabiOptions | None = None,
    transition="ge",
) -> Experiment:
    opts = TimeRabiOptions() if options is None else options
    opts.transition = transition

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
                qop.prepare_state(qubit, state=opts.transition[0])
                qop.aux_drive(qubit)
                qop.passive_reset(qubit, aux=True)
                qop.x180(
                    q=qubit,
                    length=pulse_len,
                    transition="hdawg",
                )
                # This was spectroscopy pulse
                qop.x180(qubit, transition="ge")
                # qop.qubit_spectroscopy_drive(qubit, transition="ge")
            with dsl.section(name="measure", alignment=SectionAlignment.LEFT):
                qop.measure(qubit, dsl.handles.result_handle(qubit.uid))
                qop.passive_reset(qubit)
                # Active reset
                # qop.aux_drive(qubit)
                # qop.passive_reset(qubit, aux=True)


class TimeRabiHdawg(ExperimentHandler):
    exp_name = "time_rabi"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "pulse_lengths": {"role": "x-axis", "unit": "s", "scale": 1e9},
    }

    def sequence(
        self,
        pulse_lengths,
        qu_ids=["q0"],
        transition="ge",
        options: TimeRabiOptions | None = None,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(
            self.qpu,
            qubits[0],
            pulse_lengths[0],
            transition=transition,
            options=options,
        )

    def analyze(self, path, *args, **kwargs):
        # FIXME: passing qu_uid = qu_uid causes an error, unhashable type: 'numpy.ndarray'
        return analyze_time_rabi(path=path, **kwargs)


from sqil_core.experiment import AnalysisResult, multi_qubit_handler
from sqil_core.utils import *


# TODO: ADD OPTION TO CALIBRATE ALSO FUCKING PI/2 PULSE
@multi_qubit_handler
def analyze_time_rabi(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    **kwargs,
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    lengths, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Set plot style
    sqil.set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        try:
            # Project the data and start plot
            proj, inv = sqil.fit.transform_data(y_data, inv_transform=True)
            fig, axs = plot_projection_IQ(datadict=datadict, proj_data=proj)
            anal_res.add_figure(fig, "fig", qu_id)
            # Analyze
            fit_res_exp = sqil.fit.fit_decaying_oscillations(lengths, proj)
            fit_res_const = sqil.fit.fit_oscillations(lengths, proj)
            fit_res = sqil.fit.get_best_fit(
                fit_res_exp, fit_res_const, recipe="nrmse_aic"
            )

            anal_res.add_fit(fit_res_exp, "Decaying oscillations", qu_id)
            anal_res.add_fit(fit_res_const, "Constant oscillations", qu_id)
            # Update parameters
            anal_res.add_params(
                {f"{transition}_drive_length": fit_res.metadata["pi_time"]}, qu_id
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
        qu_id,
        fit_res,
        qubit_params,
        anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
