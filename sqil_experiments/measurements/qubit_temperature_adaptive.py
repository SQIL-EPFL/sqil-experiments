import matplotlib.pyplot as plt
import numpy as np
from IPython.display import clear_output
from qu_spec import QuSpec
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *
from time_rabi import TimeRabi

from sqil_experiments.measurements.qubit_temperature import QubitTemperature


class QubitTemperatureAdaptive(ExperimentHandler):
    exp_name = "qubit_temperature_adaptive"
    db_schema = {
        "qu_freq": {"role": "data", "unit": "Hz", "scale": 1e-9},
        "qu_freq_ef": {"role": "data", "unit": "Hz", "scale": 1e-9},
        "T": {"role": "data", "unit": "K", "scale": 1e3},
        "T_std": {"role": "data", "unit": "K", "scale": 1e3},
    }

    def sequence(self, exp_params, qu_ids=["q0"], options=None, *args, **kwargs):
        (
            spec_ge_options,
            rabi_ge_options,
            spec_ef_options,
            rabi_ef_options,
            qubit_temp_options,
        ) = options
        (
            spec_ge_params,
            rabi_ge_params,
            spec_ef_params,
            rabi_ef_params,
            qubit_temp_params,
        ) = exp_params

        # Perform ge qubit spectroscopy
        qu_spec = QuSpec(qpu=self.qpu)
        qu_spec_res = qu_spec.run(
            spec_ge_params,
            transition="ge",
            qu_ids=["q0"],
            options=spec_ge_options,
            update_params=True,
            relevant_params=["readout_amplitude", "spectroscopy_amplitude"],
        )
        # If not qubit frequency is found skip
        qu_freq = qu_spec_res.updated_params.get("q0", {}).get(
            "resonance_frequency_ge", np.nan
        )
        if np.isnan(qu_freq):
            # Remove figures from memory
            plt.close("all")
            clear_output()
            return {
                "qu_freq": np.nan,
                "qu_freq_ef": np.nan,
                "T": np.nan,
                "T_std": np.nan,
            }

        # Perform ge ge time rabi
        time_rabi = TimeRabi()
        time_rabi_res = time_rabi.run(
            rabi_ge_params,
            transition="ge",
            qu_ids=["q0"],
            options=rabi_ge_options,
            update_params=True,
            relevant_params=["ge_drive_amplitude_pi", "resonance_frequency_ge"],
        )

        # Perform ef qubit spectroscopy
        qu_spec = QuSpec()
        qu_spec_res = qu_spec.run(
            spec_ef_params,
            transition="ef",
            qu_ids=["q0"],
            options=spec_ef_options,
            update_params=True,
            relevant_params=["readout_amplitude", "spectroscopy_amplitude"],
        )
        qu_spec_res.updated_params
        # If not qubit frequency is found skip
        qu_freq_ef = qu_spec_res.updated_params.get("q0", {}).get(
            "resonance_frequency_ef", np.nan
        )
        if np.isnan(qu_freq_ef):
            # Remove figures from memory
            plt.close("all")
            clear_output()
            return {
                "qu_freq": np.nan,
                "qu_freq_ef": np.nan,
                "T": np.nan,
                "T_std": np.nan,
            }

        # Perform ef ef time rabi
        time_rabi = TimeRabi()
        time_rabi_res = time_rabi.run(
            rabi_ef_params,
            transition="ef",
            qu_ids=["q0"],
            options=rabi_ef_options,
            update_params=True,
            relevant_params=["ef_drive_amplitude_pi", "resonance_frequency_ef"],
        )

        # Qubit temperature
        qubit_temp = QubitTemperature()
        qubit_temp_res = qubit_temp.run(
            qubit_temp_params,
            sweeps={"index": np.arange(10)},
            qu_ids=["q0"],
            options=qubit_temp_options,
        )

        T = qubit_temp_res.result.get("q0", {}).get("T", np.nan)
        T_std = qubit_temp_res.result.get("q0", {}).get("T_std", np.nan)

        # Remove figures from memory
        plt.close("all")
        clear_output()

        return {"qu_freq": qu_freq, "qu_freq_ef": qu_freq_ef, "T": T, "T_std": T_std}

    def analyze(self, path, *args, **kwargs):
        return analyze_qubit_temperature_adaptive(path=path, **kwargs)


@multi_qubit_handler
def analyze_qubit_temperature_adaptive(
    datadict, qpu=None, qu_id="q0", relevant_params=None, **kwargs
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    *_, sweeps = qu_data
    *_, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = []

    qu_freq = datadict["qu_freq"]
    qu_freq_ef = datadict["qu_freq_ef"]
    Ts = datadict["T"]
    T_stds = datadict["T_std"]

    Ts_mask = np.where((Ts - T_stds) > 0, T_stds, np.nan)
    Ts_masked = np.where(~np.isnan(Ts_mask), Ts, np.nan)
    Ts_masked = mask_outliers(Ts_masked)
    T_stds_masked = np.where(~np.isnan(Ts_masked), T_stds, np.nan)

    # Set plot style
    set_plot_style(plt)

    qu_freq_info = ParamInfo(f"resonance_frequency_ge")
    T_info = ParamInfo("temperature")

    qu_freq_scaled = qu_freq * qu_freq_info.scale
    T_scaled = Ts_masked * T_info.scale
    T_std_scaled = T_stds_masked * T_info.scale

    # T1 vs sweep
    fig, ax = plt.subplots(1, 1)
    anal_res.add_figure(fig, f"fig", qu_id)
    sweep_scaled = sweeps[0] * sweep_info[0].scale

    ax.errorbar(
        sweep_scaled,
        T_scaled,
        yerr=T_std_scaled,
        fmt="-o",
        capthick=2,
        elinewidth=2,
        label=T_info.name,
    )
    ax.axhline(y=np.nanmean(T_scaled), color="tab:pink", linestyle="--", label="T avg")
    ax.set_xlabel(sweep_info[0].name_and_unit)
    ax.set_ylabel(T_info.name_and_unit)
    ax.legend(loc="upper left")
    # Qubit frequency vs sweep
    ax_freq = ax.twinx()
    ax_freq.plot(
        sweep_scaled,
        qu_freq_scaled,
        "o-",
        color="tab:orange",
        alpha=0.5,
        label=qu_freq_info.name,
    )
    ax_freq.set_ylabel(qu_freq_info.name_and_unit)
    ax_freq.legend(loc="lower left")

    finalize_plot(
        fig,
        f"Qubit temperature",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    # T vs qubit frequency
    fig, ax = plt.subplots(1, 1)
    anal_res.add_figure(fig, f"fig_freq", qu_id)
    ax.errorbar(
        qu_freq_scaled,
        T_scaled,
        yerr=T_std_scaled,
        fmt="-o",
        capthick=2,
        elinewidth=2,
    )

    ax.axhline(y=np.nanmean(T_scaled), color="tab:pink", linestyle="--")
    ax.set_xlabel(qu_freq_info.name_and_unit)
    ax.set_ylabel(T_info.name_and_unit)

    finalize_plot(
        fig,
        f"Qubit temperature",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
