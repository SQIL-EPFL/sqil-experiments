# Copyright 2024 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0

"""This module defines the resonator spectroscopy experiment.

In this experiment, we sweep the resonator frequency
of a measure pulse to characterize the resonator coupled to the qubit.

The resonator spectroscopy experiment has the following pulse sequence:

    qb --- [ measure ]

This experiment only supports 1 qubit at the time, and involves only
its coupled resonator
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from laboneq import workflow
from laboneq.dsl.enums import AcquisitionType
from laboneq.simple import Experiment, SweepParameter, dsl
from laboneq.workflow.tasks import compile_experiment, run_experiment
from laboneq_applications.analysis.resonator_spectroscopy import analysis_workflow
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import (
    BaseExperimentOptions,
    ResonatorSpectroscopyExperimentOptions,
    TuneUpWorkflowOptions,
    option_field,
    task_options,
)
from laboneq_applications.tasks.parameter_updating import (
    temporary_modify,
    update_qubits,
)

if TYPE_CHECKING:
    from laboneq.dsl.quantum import TransmonParameters
    from laboneq.dsl.quantum.qpu import QPU
    from laboneq.dsl.quantum.quantum_element import QuantumElement
    from laboneq.dsl.session import Session
    from numpy.typing import ArrayLike


@task_options(base_class=BaseExperimentOptions)
class ResonatorSpectroscopyExperimentOptions:
    """Base options for the resonator spectroscopy experiment.

    Additional attributes:
        use_cw:
            Perform a CW spectroscopy where no measure pulse is played.
            Default: False.
        spectroscopy_reset_delay:
            How long to wait after an acquisition in seconds.
            Default: 1e-6.
        acquisition_type:
            Acquisition type to use for the experiment.
            Default: `AcquisitionType.SPECTROSCOPY`.
    """

    use_cw: bool = option_field(
        False, description="Perform a CW spectroscopy where no measure pulse is played."
    )
    spectroscopy_reset_delay: float = option_field(
        1e-6, description="How long to wait after an acquisition in seconds."
    )
    acquisition_type: AcquisitionType = option_field(
        AcquisitionType.SPECTROSCOPY,
        description="Acquisition type to use for the experiment.",
    )


@workflow.task
@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubit: QuantumElement,
    frequencies: ArrayLike,
    options: ResonatorSpectroscopyExperimentOptions | None = None,
) -> Experiment:
    # Define the custom options for the experiment
    opts = ResonatorSpectroscopyExperimentOptions() if options is None else options
    qubit, frequencies = validation.validate_and_convert_single_qubit_sweeps(
        qubit, frequencies
    )
    # guard against wrong options for the acquisition type
    if AcquisitionType(opts.acquisition_type) != AcquisitionType.SPECTROSCOPY:
        raise ValueError(
            "The only allowed acquisition_type for this experiment"
            "is 'AcquisitionType.SPECTROSCOPY' (or 'spectrsocopy')"
            "because it contains a sweep"
            "of the frequency of a hardware oscillator.",
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
            name=f"freq_{qubit.uid}",
            parameter=SweepParameter(f"frequencies_{qubit.uid}", frequencies),
        ) as frequency:
            qop.set_frequency(qubit, frequency=frequency, readout=True)
            if opts.use_cw:
                qop.acquire(qubit, dsl.handles.result_handle(qubit.uid))
            else:
                qop.measure(qubit, dsl.handles.result_handle(qubit.uid))
            qop.delay(qubit, opts.spectroscopy_reset_delay)


class RRSpec:
    def sequence(self):
        return create_experiment()


if __name__ == "__main__":
    exp = RRSpec()
    exp.run()
