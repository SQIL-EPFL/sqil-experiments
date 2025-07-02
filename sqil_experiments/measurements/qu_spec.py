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
        "data": {"role": "data", "unit": "V"},
        "frequencies": {"role": "x-axis", "unit": "Hz"},
    }

    def sequence(
        self,
        frequencies,
        qu_idx=0,
        options: QuSpecOptions | None = None,
        *params,
        **kwargs,
    ):
        return create_experiment(
            self.qpu, self.qpu.quantum_elements[qu_idx], frequencies, options=options
        )

    def analyze(self, path, *params, **kwargs):
        data, freq, sweep = sqil.extract_h5_data(
            path, ["data", "frequencies", "sweep0"]
        )
        options = kwargs.get("options", QuSpecOptions())
        sqil.set_plot_style(plt)

        mag = np.abs(data)
        uphase = np.unwrap(np.angle(data))

        if options.averaging_mode == AveragingMode.SINGLE_SHOT:
            fit_mag = sqil.fit.fit_lorentzian(
                freq[0], np.mean(mag[0], axis=0), sigma=np.std(mag[0], axis=0)
            )
            fit_phase = sqil.fit.fit_lorentzian(
                freq[0], np.mean(uphase[0], axis=0), sigma=np.std(uphase[0], axis=0)
            )

            fig, axs = plt.subplots(1, 2)
            axs[0].errorbar(
                freq[0],
                np.mean(mag[0], axis=0),
                np.std(mag[0], axis=0),
                fmt="-o",
                color="tab:blue",
                label="Mean with Error",
                ecolor="tab:orange",
                capsize=5,
                capthick=2,
                elinewidth=2,
                markersize=5,
            )
            axs[0].plot(freq[0], fit_mag.predict(freq[0]), "red")
            axs[0].set_title(f"Magnitude")

            axs[1].errorbar(
                freq[0],
                np.mean(uphase[0], axis=0),
                np.std(uphase[0], axis=0),
                fmt="-o",
                color="tab:blue",
                label="Mean with Error",
                ecolor="tab:orange",
                capsize=5,
                capthick=2,
                elinewidth=2,
                markersize=5,
            )
            axs[1].plot(freq[0], fit_phase.predict(freq[0]), "red")
            axs[1].set_title(f"Phase")

            fig.suptitle("Qubit specroscopy")
            fig.savefig(f"{path}/fig.png")

        else:
            fit_both = sqil.fit.fit_two_lorentzians_shared_x0(freq, mag, freq, uphase)
            x_fit = np.linspace(freq[0], freq[1], 500)

            fig, axs = plt.subplots(1, 2)

            axs[0].plot(freq, mag, "o")
            axs[0].plot(
                freq, fit_both.predict(freq, freq, *fit_both.params)[: len(freq)]
            )
            axs[0].set_title(f"Magnitude")

            axs[1].plot(freq, uphase, "o")
            axs[1].plot(
                freq, fit_both.predict(freq, freq, *fit_both.params)[len(freq) :]
            )
            axs[1].set_title(f"Phase")

            fig.suptitle("Qubit specroscopy")
            fig.savefig(f"{path}/fig.png")
