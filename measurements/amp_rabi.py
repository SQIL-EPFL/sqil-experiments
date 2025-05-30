import sqil_core as sqil
import numpy as np
import matplotlib.pyplot as plt

from laboneq.dsl.quantum import QPU
from laboneq_applications.core import validation
from laboneq.simple import Experiment, SweepParameter, dsl
from laboneq.dsl.enums import AcquisitionType, AveragingMode

from helpers.sqil_transmon.qubit import SqilTransmon
from helpers.sqil_transmon.operations import SqilTransmonOperations

from laboneq_applications.experiments.options import BaseExperimentOptions
from laboneq.workflow import option_field, task_options
from laboneq.dsl.quantum.quantum_element import QuantumElement
from numpy.typing import ArrayLike


@task_options(base_class=BaseExperimentOptions)
class AmplitudeRabiExperimentOptions:
    transition: str = option_field("ge", description="Qubit transition to drive.")
    acquisition_type: AcquisitionType = option_field(
        AcquisitionType.INTEGRATION, description="Acquisition type to use."
    )
    averaging_mode: str | AveragingMode = option_field(
        AveragingMode.CYCLIC, description="Averaging mode.", converter=AveragingMode
    )


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubit: QuantumElement,
    amplitudes: ArrayLike,
    options: AmplitudeRabiExperimentOptions | None = None,
) -> Experiment:
    opts = AmplitudeRabiExperimentOptions() if options is None else options
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
            qop.prepare_state(qubit, state=opts.transition[0])
            qop.x180(qubit, amplitude=amplitude, transition=opts.transition)
            qop.measure(qubit, dsl.handles.result_handle(qubit.uid))
            qop.passive_reset(qubit)

    return dsl.get_experiment()


class AmplitudeRabi(sqil.experiment.ExperimentHandler):
    exp_name = "amplitude_rabi"
    db_schema = {
        "data": {"type": "data"},
        "amplitudes": {"type": "axis", "plot": "x", "unit": "a.u."},
    }

    def sequence(
        self,
        amplitudes,
        qu_idx=0,
        options: AmplitudeRabiExperimentOptions | None = None,
        *params,
        **kwargs,
    ):
        return create_experiment(
            self.qpu,
            self.qpu.qubits[qu_idx],
            amplitudes,
            options=options,
        )

    def analyze(self, result, path, *params, **kwargs):
        data, amps, sweep = sqil.extract_h5_data(
            path, ["data", "amplitudes", "sweep0"]
        )
        real = np.real(data)
        imag = np.imag(data)

        # Plot 1: Real vs Imag
        fig1, ax1 = plt.subplots()
        ax1.plot(real, imag, "o-")
        ax1.set_xlabel("Re")
        ax1.set_ylabel("Im")
        ax1.set_title("IQ Plane: Real vs Imag")
        ax1.axis("equal")
        fig1.savefig(f"{path}/rabi_IQ.png")

        # Plot 2: Real vs Amplitude
        fig2, ax2 = plt.subplots()
        ax2.plot(amps, real, "o-")
        ax2.set_xlabel("Amplitude (a.u.)")
        ax2.set_ylabel("Re")
        ax2.set_title("Rabi: Re vs Amplitude")
        fig2.savefig(f"{path}/rabi_re_vs_amp.png")
