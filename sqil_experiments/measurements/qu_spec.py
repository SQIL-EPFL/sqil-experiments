# Copyright 2024 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0

"""This module defines the qubit spectroscopy experiment.

In this experiment, we sweep the frequency of a qubit drive pulse to characterize
the qubit transition frequency.

The qubit spectroscopy experiment has the following pulse sequence:

    qb --- [ prep transition ] --- [ x180_transition (swept frequency)] --- [ measure ]

If multiple qubits are passed to the `run` workflow, the above pulses are applied
in parallel on all the qubits.
"""

import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from laboneq import workflow
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.dsl.quantum.qpu import QPU
from laboneq.simple import Experiment, SweepParameter, dsl
from laboneq.workflow import option_field, task_options
from laboneq_applications.core.validation import validate_and_convert_qubits_sweeps
from laboneq_applications.experiments.options import BaseExperimentOptions
from laboneq_applications.typing import QuantumElements, QubitSweepPoints
from sqil_core.experiment import ExperimentHandler


@task_options(base_class=BaseExperimentOptions)
class QuSpecOptions:
    spectroscopy_reset_delay: float = option_field(
        1e-6, description="How long to wait after an acquisition in seconds."
    )
    acquisition_type: AcquisitionType = option_field(
        AcquisitionType.SPECTROSCOPY,
        description="Acquisition type to use for the experiment.",
    )
    averaging_mode: str | AveragingMode = option_field(
        AveragingMode.CYCLIC,
        description="Averaging mode to use for the experiment.",
        converter=AveragingMode,
    )


# @workflow.task
@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    frequencies: QubitSweepPoints,
    options: QuSpecOptions | None = None,
) -> Experiment:
    # Define the custom options for the experiment
    opts = QuSpecOptions() if options is None else options

    qubits, frequencies = validate_and_convert_qubits_sweeps(qubits, frequencies)

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
        for q, q_frequencies in zip(qubits, frequencies):
            with dsl.sweep(
                name=f"freqs_{q.uid}",
                parameter=SweepParameter(f"frequency_{q.uid}", q_frequencies),
            ) as frequency:
                qop.set_frequency(q, frequency)
                qop.qubit_spectroscopy_drive(q)
                sec = qop.measure(q, dsl.handles.result_handle(q.uid))
                # we fix the length of the measure section to the longest section among
                # the qubits to allow the qubits to have different readout and/or
                # integration lengths.
                sec.length = max_measure_section_length
                qop.passive_reset(q, delay=opts.spectroscopy_reset_delay)


class QuSpec(ExperimentHandler):
    exp_name = "qubit_spectroscopy"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "frequencies": {"role": "x-axis", "unit": "Hz", "scale": 1e-9},
    }

    def sequence(
        self,
        frequencies,
        transition="ge",
        qu_idx=0,
        options: QuSpecOptions | None = None,
        *params,
        **kwargs,
    ):
        return create_experiment(
            self.qpu, self.qpu.quantum_elements[qu_idx], frequencies, options=options
        )

    def analyze(self, path, *args, **kwargs):
        # data, freq, sweep = sqil.extract_h5_data(
        #     path, ["data", "frequencies", "sweep0"]
        # )
        # options = kwargs.get("options", QuSpecOptions())
        # sqil.set_plot_style(plt)

        # mag = np.abs(data)
        # uphase = np.unwrap(np.angle(data))

        # if options.averaging_mode == AveragingMode.SINGLE_SHOT:
        #     fit_mag = sqil.fit.fit_lorentzian(
        #         freq[0], np.mean(mag[0], axis=0), sigma=np.std(mag[0], axis=0)
        #     )
        #     fit_phase = sqil.fit.fit_lorentzian(
        #         freq[0], np.mean(uphase[0], axis=0), sigma=np.std(uphase[0], axis=0)
        #     )

        #     fig, axs = plt.subplots(1, 2)
        #     axs[0].errorbar(
        #         freq[0],
        #         np.mean(mag[0], axis=0),
        #         np.std(mag[0], axis=0),
        #         fmt="-o",
        #         color="tab:blue",
        #         label="Mean with Error",
        #         ecolor="tab:orange",
        #         capsize=5,
        #         capthick=2,
        #         elinewidth=2,
        #         markersize=5,
        #     )
        #     axs[0].plot(freq[0], fit_mag.predict(freq[0]), "red")
        #     axs[0].set_title(f"Magnitude")

        #     axs[1].errorbar(
        #         freq[0],
        #         np.mean(uphase[0], axis=0),
        #         np.std(uphase[0], axis=0),
        #         fmt="-o",
        #         color="tab:blue",
        #         label="Mean with Error",
        #         ecolor="tab:orange",
        #         capsize=5,
        #         capthick=2,
        #         elinewidth=2,
        #         markersize=5,
        #     )
        #     axs[1].plot(freq[0], fit_phase.predict(freq[0]), "red")
        #     axs[1].set_title(f"Phase")

        #     fig.suptitle("Qubit specroscopy")
        #     fig.savefig(f"{path}/fig.png")

        # else:
        #     fit_both = sqil.fit.fit_two_lorentzians_shared_x0(freq, mag, freq, uphase)
        #     x_fit = np.linspace(freq[0], freq[1], 500)

        #     fig, axs = plt.subplots(1, 2)

        #     axs[0].plot(freq, mag, "o")
        #     axs[0].plot(
        #         freq, fit_both.predict(freq, freq, *fit_both.params)[: len(freq)]
        #     )
        #     axs[0].set_title(f"Magnitude")

        #     axs[1].plot(freq, uphase, "o")
        #     axs[1].plot(
        #         freq, fit_both.predict(freq, freq, *fit_both.params)[len(freq) :]
        #     )
        #     axs[1].set_title(f"Phase")

        #     fig.suptitle("Qubit specroscopy")
        #     fig.savefig(f"{path}/fig.png")
        # TODO: Add support for other transitions
        return qu_spec_analysis(path=path, **kwargs)


from sqil_core.experiment import AnalysisResult
from sqil_core.fit import FitQuality
from sqil_core.utils import *

from sqil_experiments.analysis.fit import find_shared_peak

# map_data_dict, extract_h5_data, param_info_from_schema, enrich_qubit_params, get_relevant_exp_parameters, plot_mag_phase, ONE_TONE_PARAMS, ParamInfo


def qu_spec_analysis(
    path=None,
    datadict=None,
    qpu=None,
    at_idx=None,
    transition="ge",
    qu_uid="q0",
    relevant_params=["spectroscopy_amplitude"],
    **kwargs,
) -> AnalysisResult:
    # Prepare analysis result object
    anal_res = AnalysisResult()
    anal_res.updated_params[qu_uid] = {}
    fit_res = None

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
    anal_res.updated_params[qu_uid] = {}
    fit_res = None

    has_sweeps = y_data.ndim > 1

    sqil.set_plot_style(plt)

    if not has_sweeps:
        # Plot without fit
        fig, axs = plot_mag_phase(datadict=datadict)
        anal_res.figures.update({"fig": fig})

        # Fit data to extract parameters
        try:
            is_wide_range = x_data[-1] - x_data[0] > 200e6
            mag, phase = np.abs(y_data), np.unwrap(np.angle(y_data))
            fit_res, trace = find_shared_peak(x_data, mag, phase, full_output=True)
        except Exception as e:
            print(f"Error while fitting", e)
        if fit_res is not None:
            anal_res.fits.update({"Combined mag-phase fit": fit_res})
            param_id = f"resonance_frequency_{transition}"
            anal_res.updated_params[qu_uid].update(
                {param_id: fit_res.params_by_name["x0"]}
            )
            x_fit = np.linspace(x_data[0], x_data[-1], np.max([2000, len(x_data)]))

            if trace in ["mag", "phase"]:
                ax_idx = 1
                y_fit_scaled = fit_res.predict(x_fit)
                if trace == "mag":
                    ax_idx = 0
                    y_fit_scaled *= y_info.scale
                axs[ax_idx].plot(x_fit * x_info.scale, y_fit_scaled, color="tab:red")
            elif trace == "both":
                y_fit = fit_res.predict(x_fit, x_fit, *fit_res.params)
                y_fit_mag = y_fit[: len(x_fit)] * y_info.scale
                y_fit_phase = y_fit[len(x_fit) :]
                axs[0].plot(x_fit * x_info.scale, y_fit_mag, color="tab:red")
                axs[1].plot(x_fit * x_info.scale, y_fit_phase, color="tab:red")
    else:
        fig, axs = plot_mag_phase(datadict=datadict)
        anal_res.figures.update({"fig": fig})
        fit_res = None

    finalize_plot(
        fig,
        f"Qubit spectroscopy ({transition})",
        fit_res,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params[qu_uid],
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )
    fig.tight_layout()

    return anal_res
