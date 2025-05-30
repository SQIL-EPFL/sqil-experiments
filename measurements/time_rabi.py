import sqil_core as sqil
import numpy as np
import matplotlib.pyplot as plt

from laboneq.dsl.quantum import QPU
from laboneq.simple import (
    Experiment,
    SweepParameter,
    dsl,
    pulse_library,
    SectionAlignment,
)
from laboneq.dsl.enums import AcquisitionType, AveragingMode

from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from laboneq.workflow import option_field, task_options

from laboneq.dsl.quantum.quantum_element import QuantumElement
from numpy.typing import ArrayLike

import sys

sys.path.append(r"Z:\Projects\BottomLoader\Measurement\analysis_code")
from inspection import inspect_decaying_oscillations


@task_options(base_class=BaseExperimentOptions)
class TimeRabiExperimentOptions:
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
    options: TimeRabiExperimentOptions | None = None,
) -> Experiment:
    opts = TimeRabiExperimentOptions() if options is None else options
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
                qop.rx(
                    q=qubit,
                    angle=None,
                    amplitude=1,
                    length=pulse_len + 20e-9,
                )
            with dsl.section(name="measure", alignment=SectionAlignment.LEFT):
                qop.measure(qubit, dsl.handles.result_handle(qubit.uid))
                qop.passive_reset(qubit)


class TimeRabi(sqil.experiment.ExperimentHandler):
    exp_name = "time_rabi"
    db_schema = {
        "data": {"type": "data"},
        "pulse_lengths": {"type": "axis", "plot": "x", "unit": "s"},
    }

    def sequence(
        self,
        pulse_lengths,
        qu_idx=0,
        options: TimeRabiExperimentOptions | None = None,
        *params,
        **kwargs,
    ):
        return create_experiment(
            self.qpu,
            self.qpu.qubits[qu_idx],
            pulse_lengths,
            options=options,
        )

    def analyze(self, result, path, *params, **kwargs):
        data, lengths, sweep = sqil.extract_h5_data(
            path, ["data", "pulse_lengths", "sweep0"]
        )

        inspect_decaying_oscillations(lengths, data)

        # re = np.real(data)
        # im = np.imag(data)

        # Plot IQ (real vs imag)
        # fig1, ax1 = plt.subplots()
        # ax1.plot(re, im, "o-")
        # ax1.set_xlabel("Re")
        # ax1.set_ylabel("Im")
        # ax1.set_title("IQ Plane: Real vs Imag")
        # ax1.axis("equal")
        # fig1.savefig(f"{path}/time_rabi_IQ.png")

        # # Plot real vs pulse length
        # fig2, ax2 = plt.subplots()
        # ax2.plot(lengths, im, "o-")
        # ax2.set_xlabel("Pulse Length (s)")
        # ax2.set_ylabel("Re")
        # ax2.set_title("Rabi: Re vs Pulse Duration")
        # fig2.savefig(f"{path}/time_rabi_re_vs_length.png")
