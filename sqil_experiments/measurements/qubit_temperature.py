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
class QubitTemperatureOptions:
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
    amplitudes: ArrayLike,
    options: QubitTemperatureOptions | None = None,
    transition="ge",
) -> Experiment:
    opts = QubitTemperatureOptions() if options is None else options
    opts.transition = transition

    qubit, amplitudes = validation.validate_and_convert_single_qubit_sweeps(
        qubit, amplitudes
    )
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
            name=f"amp_{qubit.uid}",
            parameter=SweepParameter(f"amplitude_{qubit.uid}", amplitudes),
        ) as amplitude:
            qop.x180(qubit, amplitude=amplitude, transition="ef")
            qop.measure(qubit, dsl.handles.result_handle(f"{qubit.uid}/data_no_pi"))
            qop.passive_reset(qubit)

            qop.prepare_state(qubit, state="e")
            qop.x180(qubit, amplitude=amplitude, transition="ef")
            qop.measure(qubit, dsl.handles.result_handle(f"{qubit.uid}/data_pi"))
            qop.passive_reset(qubit)


class QubitTemperature(ExperimentHandler):
    exp_name = "qubit_temperature"
    db_schema = {
        "data_no_pi": {"role": "data", "unit": "V", "scale": 1e3},
        "data_pi": {"role": "data", "unit": "V", "scale": 1e3},
        "amplitude": {"role": "x-axis", "unit": "", "scale": 1e3},
    }

    def sequence(
        self,
        amplitude,
        qu_ids=["q0"],
        options: QubitTemperatureOptions | None = None,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(
            self.qpu,
            qubits[0],
            amplitude[0],
            options=options,
        )

    def analyze(self, path, *args, **kwargs):
        return analyze_qubit_temperature(path=path, **kwargs)


from sqil_core.experiment import AnalysisResult, multi_qubit_handler
from sqil_core.utils import *


@multi_qubit_handler
def analyze_qubit_temperature(
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

    # A_no_ge = np.mean(proj_no_pi)

    h = 6.6e-34
    kb = 1.38e-23
    qu_freq = 5.35e9

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"ef_drive_amplitude_pi"]

    # TODO: define datas here - maybe make a fake datadict

    # Set plot style
    sqil.set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        try:
            # Extract and project the data
            amplitudes = datadict["amplitude"]
            proj_no_pi = sqil.fit.transform_data(datadict["data_no_pi"])
            proj_pi = sqil.fit.transform_data(datadict["data_pi"])

            # Plot
            fig, axs = plot_projection_IQ(datadict=datadict, proj_data=proj_no_pi)
            anal_res.add_figure(fig, "fig", qu_id)
            # Add pi data to plot
            axs[0].plot(
                amplitudes * x_info.scale,
                proj_pi * y_info.scale,
                "o",
                color="tab:orange",
            )
            axs[1].plot(
                np.real(datadict["data_pi"]) * y_info.scale,
                np.imag(datadict["data_pi"]) * y_info.scale,
                "o",
                color="tab:orange",
            )
            axs[0].legend([r"without $\pi$-pulse", r"with $\pi$-pulse"])

            print(
                np.real(datadict["data_no_pi"]) * y_info.scale,
                np.imag(datadict["data_no_pi"]) * y_info.scale,
            )
            print(
                np.real(datadict["data_pi"]) * y_info.scale,
                np.imag(datadict["data_pi"]) * y_info.scale,
            )

            P_e_array = 1 - proj_pi / (proj_pi + proj_no_pi)
            T_qu_array = h * qu_freq / (kb * np.log(1 / P_e_array - 1))

            T_qu = np.mean(T_qu_array)
            T_qu_error = np.std(T_qu_array)

        except Exception as e:
            print("Error while fitting projected data", e)

    elif has_sweeps:
        fig, axs = plot_mag_phase(datadict=datadict, raw=True)

    finalize_plot(
        fig,
        f"Qubit temperature {T_qu*1e3:.1f} mK",
        qu_id,
        fit_res,
        qubit_params,
        anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
