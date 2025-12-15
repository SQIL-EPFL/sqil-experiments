import matplotlib.pyplot as plt
import numpy as np
from IPython.display import clear_output
from qu_spec import QuSpec
from qu_spec_hdawg import QuSpecHdawg
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *
from time_rabi import TimeRabi

from sqil_experiments.measurements.T1_adaptive import analyze_T1_adaptive
from sqil_experiments.measurements.T1_hdawg import T1_hdawg
from sqil_experiments.measurements.time_rabi_hdawg import TimeRabiHdawg


class T1Adaptive_hdawg(ExperimentHandler):
    exp_name = "T1_adaptive_hdawg"
    db_schema = {
        "qu_freq": {"role": "data", "unit": "Hz", "scale": 1e-9},
        "T1": {"role": "data", "unit": "s", "scale": 1e6},
        "T1_std": {"role": "data", "unit": "s", "scale": 1e6},
    }

    def sequence(
        self, exp_params, qu_ids=["q0"], transition="ge", options=None, *args, **kwargs
    ):
        spec_options_t, rabi_options_t, spec_options_f, rabi_options_f, T1_options = (
            options
        )
        spec_params_t, rabi_params_t, spec_params_f, rabi_params_f, T1_params = (
            exp_params
        )

        #### TRANSMON CALIBRATION ####
        # Perform qubit spectroscopy
        qu_spec = QuSpec(qpu=self.qpu)
        qu_spec_res = qu_spec.run(
            spec_params_t,
            transition=transition,
            qu_ids=["q0"],
            options=spec_options_t,
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
            rabi_params_t,
            transition=transition,
            qu_ids=["q0"],
            options=rabi_options_t,
            update_params=True,
            relevant_params=["ge_drive_amplitude_pi", "resonance_frequency_ge"],
        )

        #### FLUXONIUM CALIBRATION ####
        # Perform qubit spectroscopy
        qu_spec = QuSpecHdawg(qpu=self.qpu)
        qu_spec_res = qu_spec.run(
            spec_params_f,
            transition="hdawg",
            qu_ids=["q0"],
            options=spec_options_f,
            update_params=True,
            relevant_params=["readout_amplitude", "spectroscopy_amplitude"],
        )
        # If not qubit frequency is found skip
        qu_freq = qu_spec_res.updated_params.get("q0", {}).get(
            "resonance_frequency_hdawg", np.nan
        )
        if np.isnan(qu_freq):
            return {"qu_freq": np.nan, "T1": np.nan}

        # Perform time rabi
        time_rabi = TimeRabiHdawg()
        time_rabi_res = time_rabi.run(
            rabi_params_f,
            transition=transition,
            qu_ids=["q0"],
            options=rabi_options_f,
            update_params=True,
            relevant_params=["ge_drive_amplitude_pi", "resonance_frequency_ge"],
        )

        # Perform T1 experiment
        T1_exp = T1_hdawg()
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
