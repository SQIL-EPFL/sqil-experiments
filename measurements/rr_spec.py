import sqil_core as sqil
import numpy as np
import matplotlib.pyplot as plt

# from rr_spec import create_experiment
from laboneq.dsl.quantum import QPU
from laboneq_applications.qpu_types.tunable_transmon import (
    TunableTransmonOperations,
    TunableTransmonQubit,
)
from helpers.sqil_transmon.qubit import SqilTransmon
from helpers.sqil_transmon.operations import SqilTransmonOperations

from laboneq_applications.experiments.options import (
    ResonatorSpectroscopyExperimentOptions,
)
from laboneq_applications.core import validation
from laboneq.dsl.enums import AcquisitionType
from laboneq.simple import Experiment, SweepParameter, dsl

from laboneq.dsl.quantum.quantum_element import QuantumElement
from numpy.typing import ArrayLike

from helpers.plottr import DataDict, DDH5Writer


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


class RRSpec(sqil.experiment.ExperimentHandler):
    db_schema = {
        "data": {"type": "data"},
        "frequencies": {"type": "axis", "unit": "Hz"},
    }
    exp_name = "rr spectroscopy"

    def sequence(self, qu_idx, frequencies):
        self.qpu.qubits[qu_idx].update(
            **{
                "drive_lo_frequency": 5e9,
                "readout_lo_frequency": 7.2e9,
                "readout_resonator_frequency": 7.4e9,
            }
        )
        return create_experiment(self.qpu, self.qpu.qubits[qu_idx], frequencies)

    def analyze(self, result, *params, **kwargs):
        data = result["q0"]["result"].data
        frequencies = params[1]

        fig, ax = plt.subplots(1, 1)
        ax.plot(frequencies, np.abs(data))

        # datadict =

        # with DDH5Writer(datadict, db_path_local, name=exp_name) as writer:
        #     filepath_parent = writer.filepath.parent

        #     # take the last two stages of the filepath_parent
        #     path = str(filepath_parent)
        #     last_two_parts = path.split(os.sep)[-2:]
        #     new_path = os.path.join(db_path, *last_two_parts)
        #     writer.save_text("#path.md", new_path)

        #     writer.add_data(
        #         readout_delay=frequencies,
        #         data=data,
        #     )
        #     fig.savefig(f"{os.path.join(db_path_local, *last_two_parts)}/fig.png")
