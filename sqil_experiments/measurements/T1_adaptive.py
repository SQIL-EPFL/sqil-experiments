import matplotlib.pyplot as plt
import numpy as np
from IPython.display import clear_output
from qu_spec import QuSpec
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *
from time_rabi import TimeRabi

from sqil_experiments.measurements.T1 import T1


class T1Adaptive(ExperimentHandler):
    exp_name = "T1_adaptive"
    db_schema = {
        "qu_freq": {"role": "data", "unit": "Hz", "scale": 1e-9},
        "T1": {"role": "data", "unit": "s", "scale": 1e6},
        "T1_std": {"role": "data", "unit": "s", "scale": 1e6},
    }

    def sequence(
        self, exp_params, qu_ids=["q0"], transition="ge", options=None, *args, **kwargs
    ):
        spec_options, rabi_options, T1_options = options
        spec_params, rabi_params, T1_params = exp_params

        # Perform qubit spectroscopy
        qu_spec = QuSpec(qpu=self.qpu)
        qu_spec_res = qu_spec.run(
            spec_params,
            transition=transition,
            qu_ids=["q0"],
            options=spec_options,
            update_params=True,
            relevant_params=["readout_amplitude", "spectroscopy_amplitude"],
        )
        # If not qubit frequency is found skip
        qu_freq = qu_spec_res.updated_params.get("q0", {}).get(
            "resonance_frequency_ge", np.nan
        )
        if np.isnan(qu_freq):
            return {"qu_freq": np.nan, "T1": np.nan}

        # Perform time rabi
        time_rabi = TimeRabi()
        time_rabi_res = time_rabi.run(
            rabi_params,
            transition=transition,
            qu_ids=["q0"],
            options=rabi_options,
            update_params=True,
            relevant_params=["ge_drive_amplitude_pi", "resonance_frequency_ge"],
        )

        T1_exp = T1()
        # Automatically compute T1 sweep times
        if not T1_params:
            T1_value = T1_exp.qpu.quantum_elements[0].parameters.ge_T1
            if T1_value > 1e-3:
                T1_value = 50e-6
            time = np.hstack(
                [
                    np.linspace(0, T1_value, 11),
                    np.logspace(
                        np.log(T1_value * 1.1), np.log(5 * T1_value), 11, base=np.e
                    ),
                ]
            )
            T1_params = [time]
        # Perform T1 experiment
        T1_res = T1_exp.run(
            T1_params,
            options=T1_options,
            update_params=True,
        )

        # Extract fitted T1 value and standard error
        T1_extracted = T1_res.updated_params.get("q0", {}).get("ge_T1", np.nan)
        T1_std = np.nan
        if not np.isnan(T1_extracted):
            try:
                T1_std = T1_res.fits["q0 - fit"].std_err[1]
            except _:
                pass

        # Remove figures from memory
        plt.close("all")
        clear_output()

        return {"qu_freq": qu_freq, "T1": T1_extracted, "T1_std": T1_std}

    def analyze(self, path, *args, **kwargs):
        return analyze_T1_adaptive(path=path, **kwargs)


@multi_qubit_handler
def analyze_T1_adaptive(
    datadict, qpu=None, qu_id="q0", transition="ge", relevant_params=None, **kwargs
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
    T1s = datadict["T1"]
    T1_stds = datadict["T1_std"]

    T1s_masked = np.where(T1s > 0, T1s, np.nan)
    T1s_masked = mask_outliers(T1s_masked)
    T1_stds_masked = np.where(~np.isnan(T1s_masked), T1_stds, np.nan)
    # Update parameters
    anal_res.add_params({f"{transition}_T1": np.nanmean(T1s_masked)}, qu_id)

    # Set plot style
    set_plot_style(plt)

    qu_freq_info = ParamInfo(f"resonance_frequency_{transition}")
    T1_info = ParamInfo(f"{transition}_T1")

    qu_freq_scaled = qu_freq * qu_freq_info.scale
    T1_scaled = T1s_masked * T1_info.scale
    T1_std_scaled = T1_stds_masked * T1_info.scale

    # T1 vs sweep
    fig, ax = plt.subplots(1, 1)
    anal_res.add_figure(fig, f"fig", qu_id)
    sweep_scaled = sweeps[0] * sweep_info[0].scale

    ax.errorbar(
        sweep_scaled,
        T1_scaled,
        yerr=T1_std_scaled,
        fmt="-o",
        capthick=2,
        elinewidth=2,
        label=T1_info.name,
    )
    ax.axhline(
        y=np.nanmean(T1_scaled), color="tab:pink", linestyle="--", label="T1 avg"
    )
    ax.set_xlabel(sweep_info[0].name_and_unit)
    ax.set_ylabel(T1_info.name_and_unit)
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
        f"T1 ({transition})",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    # T1 vs qubit frequency
    fig, ax = plt.subplots(1, 1)
    anal_res.add_figure(fig, f"fig_freq", qu_id)
    ax.errorbar(
        qu_freq_scaled,
        T1_scaled,
        yerr=T1_std_scaled,
        fmt="-o",
        capthick=2,
        elinewidth=2,
    )

    ax.axhline(y=np.nanmean(T1_scaled), color="tab:pink", linestyle="--")
    ax.set_xlabel(qu_freq_info.name_and_unit)
    ax.set_ylabel(T1_info.name_and_unit)

    finalize_plot(
        fig,
        f"T1 ({transition})",
        qu_id,
        fit_res=None,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
