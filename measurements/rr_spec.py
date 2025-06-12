import sqil_core as sqil
from sqil_core.experiment import ExperimentHandler

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
    BaseExperimentOptions,
)
from laboneq_applications.core import validation
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.simple import Experiment, SweepParameter, dsl

from laboneq.dsl.quantum.quantum_element import QuantumElement
from numpy.typing import ArrayLike

from helpers.plottr import DataDict, DDH5Writer

from laboneq.workflow import (
    option_field,
    task_options,
    workflow_options,
)


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
    averaging_mode: str | AveragingMode = option_field(
        AveragingMode.CYCLIC,
        description="Averaging mode to use for the experiment.",
        converter=AveragingMode,
    )


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


class RRSpec(ExperimentHandler):
    exp_name = "resonator_spectroscopy"
    db_schema = {
        "data": {"type": "data"},
        "frequencies": {"type": "axis", "plot": "x", "unit": "Hz"},
    }

    def sequence(
        self,
        frequencies,
        qu_idx=0,
        options: ResonatorSpectroscopyExperimentOptions | None = None,
        *params,
        **kwargs,
    ):
        # self.qpu.qubits[qu_idx].update(
        #     **{
        #         "drive_lo_frequency": 5e9,
        #         "readout_lo_frequency": 5e9,
        #         "readout_resonator_frequency": 5e9,
        #     }
        # )
        return create_experiment(
            self.qpu, self.qpu.quantum_elements[qu_idx], frequencies, options=options
        )

    def analyze(self, path, *params, **kwargs):
        data, freq, sweep = sqil.extract_h5_data(
            path, ["data", "frequencies", "sweep0"]
        )
        options = kwargs.get("options", ResonatorSpectroscopyExperimentOptions())

        result = None

        if options.averaging_mode == AveragingMode.SINGLE_SHOT:
            fig, ax = plt.subplots(1, 1, figsize=(16, 5))
            linmag = np.abs(data[0])
            ax.errorbar(
                freq[0],
                np.mean(linmag, axis=0),
                np.std(linmag, axis=0),
                fmt="-o",
                color="tab:blue",
                label="Mean with Error",
                ecolor="tab:orange",
                capsize=5,
                capthick=2,
                elinewidth=2,
                markersize=5,
            )
        else:
            is1D = np.array(data).ndim == 1
            if is1D:
                fig, ax = plt.subplots(1, 1)
                ax.plot(freq, np.abs(data))
            else:
                fig, ax = plt.subplots(1, 1)
                ax.pcolormesh(freq, sweep, np.abs(data))

        fig.savefig(f"{path}/fig.png")
