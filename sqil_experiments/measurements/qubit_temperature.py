import sys

import matplotlib.pyplot as plt
import numpy as np
import sqil_core.fit as fit
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from laboneq.simple import Experiment, SweepParameter, dsl
from laboneq.workflow import option_field, task_options
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from numpy.typing import ArrayLike
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *


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


@multi_qubit_handler
def analyze_qubit_temperature(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    qu_freq=None,
    fit_kwargs=None,
    **kwargs,
):
    if fit_kwargs is None:
        fit_kwargs = {}

    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    amplitudes, _, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"ef_drive_amplitude_pi"]

    # TODO: define datas here - maybe make a fake datadict
    P_e = np.nan
    T_qu, T_qu_std = np.nan, np.nan
    qu_freq = getattr(
        qpu[qu_id].parameters, f"resonance_frequency_{transition}", np.nan
    )

    # Set plot style
    set_plot_style(plt)

    has_sweeps = (len(sweeps)) > 0
    if not has_sweeps:
        # Prepare plot
        fig, axs = make_plot_frame(plot_type="IQ")
        anal_res.add_figure(fig, "fig", qu_id)

        try:
            # Extract and project the data
            proj_no_pi, inv_no_pi = fit.transform_data(
                datadict["data_no_pi"], inv_transform=True
            )
            proj_pi, inv_pi = fit.transform_data(
                datadict["data_pi"], inv_transform=True
            )

            # Add pi data to plot
            for proj, key in zip([proj_no_pi, proj_pi], ["data_no_pi", "data_pi"]):
                axs[0].plot(
                    amplitudes * x_info.scale,
                    proj * y_info.scale,
                    "o",
                    label=key.replace("_", " "),
                )

                axs[1].plot(
                    np.real(datadict[key]) * y_info.scale,
                    np.imag(datadict[key]) * y_info.scale,
                    "o",
                )
            axs[0].legend()

        except Exception as e:
            print("Error while extracting or projecting data", e)

        try:
            T_qu, T_qu_std, P_e, P_e_std = np.nan, np.nan, np.nan, np.nan
            fits = None
            if len(amplitudes) == 2:
                T_qu, P_e, fits = compute_qubit_temp_amp_two_points(
                    proj_pi, proj_no_pi, qu_freq, fit_kwargs=fit_kwargs
                )
            else:
                (T_qu, T_qu_std), (P_e, P_e_std), fits = (
                    compute_qubit_temp_amplitude_fitted(
                        amplitudes, proj_pi, proj_no_pi, qu_freq, fit_kwargs=fit_kwargs
                    )
                )
                x_fit = np.linspace(amplitudes[0], amplitudes[-1], 200)
                for fit_res, inv in zip(fits, (inv_no_pi, inv_pi)):
                    inv_fit = inv(fit_res.predict(x_fit))
                    axs[0].plot(
                        x_fit * x_info.scale,
                        fit_res.predict(x_fit) * y_info.scale,
                        "tab:red",
                    )
                    axs[1].plot(
                        inv_fit.real * y_info.scale,
                        inv_fit.imag * y_info.scale,
                        "tab:red",
                    )

            anal_res.add_output({"T": T_qu, "P_e": P_e}, qu_id)

        except Exception as e:
            print("Error extracting temperature from data", e)

    else:
        idx = sweeps[0]
        T_qu_arr, P_e_arr = np.ones(len(sweeps[0])), np.ones(len(sweeps[0]))
        for i in range(len(idx)):
            # Extract and project the data
            amplitudes = datadict["amplitude"][i]
            proj_no_pi = fit.transform_data(datadict["data_no_pi"][i])
            proj_pi = fit.transform_data(datadict["data_pi"][i])

            if len(amplitudes) == 2:
                T_qu, P_e, fits = compute_qubit_temp_amp_two_points(
                    proj_pi, proj_no_pi, qu_freq, fit_kwargs=fit_kwargs
                )
            else:
                (T_qu, _), (P_e, _), fits = compute_qubit_temp_amplitude_fitted(
                    amplitudes, proj_pi, proj_no_pi, qu_freq, fit_kwargs=fit_kwargs
                )
            T_qu_arr[i], P_e_arr[i] = T_qu, P_e

        T_qu_arr, P_e_arr = mask_outliers(T_qu_arr), mask_outliers(P_e_arr)
        T_qu, T_qu_std = np.nanmean(T_qu_arr), np.nanstd(T_qu_arr)
        P_e, P_e_std = np.nanmean(P_e_arr), np.nanstd(P_e_arr)
        anal_res.add_output(
            {"T": T_qu, "T_std": T_qu_std, "P_e": P_e, "P_e_std": P_e_std}, qu_id
        )

        perc10, perc90 = np.nanpercentile(T_qu_arr, [10, 90])
        fig, ax = plt.subplots(1, 1)
        anal_res.add_figure(fig, "fig", qu_id)

        if sweep_info[0].id == "index":
            # ax.plot(sweeps[0] * sweep_info[0].scale, T_qu_arr * 1e3, "o")
            ax.hist(T_qu_arr * 1e3, alpha=0.8)  # , bins=len(T_qu_arr)//3
            ax.axvline(
                np.nanmean(T_qu_arr) * 1e3, color="black", linestyle="--", label="Mean"
            )
            ax.axvline(
                np.nanmedian(T_qu_arr) * 1e3,
                color="tab:orange",
                linestyle="--",
                label="Median",
            )

            ax.axvline(
                perc10 * 1e3, color="tab:pink", linestyle="-.", label="10th percentile"
            )
            ax.axvline(
                perc90 * 1e3,
                color="tab:purple",
                linestyle="-.",
                label="90th percentile",
            )

            ax.set_xlabel("Temperature [mK]")
            ax.set_ylabel("Distribution")
            ax.legend()

        else:
            ax.plot(sweeps[0] * sweep_info[0].scale, T_qu_arr * 1e3, "o")
            ax.set_xlabel(sweep_info[0].name_and_unit)
            ax.set_ylabel("Temperature [mK]")
            ax.legend()

    title = (
        f"Qubit temperature {T_qu*1e3:.1f}"
        + r"$\pm$"
        + f"{T_qu_std*1e3:.1f}"
        + " mK"
        + f"\n$P_e$ / $P_g$ = {P_e*100:.2f} %"
    )
    finalize_plot(
        fig,
        title,
        qu_id,
        fit_res,
        qubit_params,
        anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res


def compute_qubit_temp_amplitude_fitted(
    amplitudes, proj_pi, proj_no_pi, qu_freq, fit_kwargs=None
):
    if fit_kwargs is None:
        fit_kwargs = {}

    fit_res_no_pi = fit.fit_oscillations(amplitudes, proj_no_pi, **fit_kwargs)
    fit_res_pi = fit.fit_oscillations(amplitudes, proj_pi, **fit_kwargs)

    A_no_pi = np.abs(fit_res_no_pi.params_by_name["A"])
    A_no_pi_std = np.abs(fit_res_no_pi.std_err[0])
    A_pi = np.abs(fit_res_pi.params_by_name["A"])
    A_pi_std = np.abs(fit_res_pi.std_err[0])

    P_e, P_e_std = P_e_and_fit_error(A_pi, A_no_pi, A_pi_std, A_no_pi_std)
    T_qu, T_qu_std = T_qu_and_fit_error(P_e, P_e_std, qu_freq)

    if T_qu < 0:
        return (np.nan, np.nan), (np.nan, np.nan), None

    return (T_qu, T_qu_std), (P_e, P_e_std), (fit_res_no_pi, fit_res_pi)


def P_e_and_fit_error(A_pi, A_no_pi, sigma_A_pi, sigma_A_no_pi):
    """
    Compute P_e and its propagated standard deviation.
    """
    D = A_pi + A_no_pi
    Pe = A_no_pi / D

    sigma_Pe = (
        1.0
        / D**2
        * np.sqrt((A_no_pi**2) * sigma_A_pi**2 + (A_pi**2) * sigma_A_no_pi**2)
    )

    return Pe, sigma_Pe


def T_qu_and_fit_error(Pe, sigma_Pe, qu_freq):
    """
    Compute T_qu and its propagated standard deviation from P_e.
    """
    h = 6.6e-34
    kb = 1.38e-23

    L = np.log(1.0 / Pe - 1.0)
    C = h * qu_freq / kb

    Tqu = C / L

    sigma_Tqu = C / (L**2 * Pe * (1.0 - Pe)) * sigma_Pe

    return Tqu, sigma_Tqu


def compute_qubit_temp_amp_two_points(proj_pi, proj_no_pi, qu_freq, fit_kwargs=None):
    h = 6.6e-34
    kb = 1.38e-23

    if fit_kwargs is None:
        fit_kwargs = {}

    A_no_pi = np.abs(proj_no_pi[1] - proj_no_pi[0])
    A_pi = np.abs(proj_pi[1] - proj_pi[0])

    P_e = 1 - A_pi / (A_pi + A_no_pi)
    T_qu = h * qu_freq / (kb * np.log(1 / P_e - 1))

    if T_qu < 0:
        return np.nan, np.nan, (None, None)

    return T_qu, P_e, (None, None)
