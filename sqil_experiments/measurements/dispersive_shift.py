import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from laboneq.dsl.enums import AcquisitionType, AveragingMode

# from rr_spec import create_experiment
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from laboneq.simple import Experiment, SectionAlignment, SweepParameter, dsl
from laboneq.workflow import option_field, task_options
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from numpy.typing import ArrayLike
from sqil_core.experiment import AnalysisResult, ExperimentHandler

from sqil_experiments.measurements.rr_spec import rr_spec_analysis


@task_options(base_class=BaseExperimentOptions)
class DispersiveShiftOptions:
    averaging_mode: str | AveragingMode = option_field(
        AveragingMode.CYCLIC,
        description="Averaging mode to use for the experiment.",
        converter=AveragingMode,
    )
    acquisition_type: AcquisitionType = option_field(
        AcquisitionType.SPECTROSCOPY, description="Acquisition type."
    )
    transition: str = option_field("ge", description="Transition to measure.")


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubit: QuantumElement,
    frequencies: ArrayLike,
    options: DispersiveShiftOptions | None = None,
    transition="ge",
) -> Experiment:
    # Define the custom options for the experiment
    opts = DispersiveShiftOptions() if options is None else options
    opts.transition = transition
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

            with dsl.section(
                name=f"state {opts.transition[0]}", alignment=SectionAlignment.RIGHT
            ):
                qop.prepare_state.omit_section(qubit, state=opts.transition[0])
                qop.measure(qubit, dsl.handles.result_handle(f"{qubit.uid}/data_g"))
                qop.passive_reset(qubit)

            with dsl.section(
                name=f"state {opts.transition[1]}", alignment=SectionAlignment.RIGHT
            ):
                qop.prepare_state(qubit, state=opts.transition[1])
                qop.measure(qubit, dsl.handles.result_handle(f"{qubit.uid}/data_e"))
                qop.passive_reset(qubit)


class DispersiveShift(ExperimentHandler):
    exp_name = "dispersive_shift"
    db_schema = {
        "data_g": {"role": "data", "unit": "V", "scale": 1e3},
        "data_e": {"role": "data", "unit": "V", "scale": 1e3},
        "readout_resonator_frequency": {
            "role": "x-axis",
            "unit": "Hz",
            "scale": 1e-9,
        },  # FIXME: changing this name adds an extra dimension to the data
        # YES! it must have the same name as he input arguemnt!
    }

    def sequence(
        self,
        readout_resonator_frequency: list,
        qu_ids=["q0"],
        options: DispersiveShiftOptions | None = None,
        *params,
        **kwargs,
    ):
        if len(qu_ids) > 1:
            raise ValueError("Only one qubit at the time is allowed")
        qubit = self.qpu[qu_ids[0]]
        return create_experiment(
            self.qpu,
            qubit,
            readout_resonator_frequency[0],
            options=options,
        )

    def analyze(self, path, *args, **kwargs):
        anal_res: AnalysisResult = AnalysisResult()

        datadict = sqil.extract_h5_data(path, get_metadata=True)

        schema_g = {**datadict["metadata"]["schema"]}
        schema_e = {**datadict["metadata"]["schema"]}

        del schema_g["data_e"]
        del schema_e["data_g"]

        datadict["metadata"]["schema"] = schema_g
        anal_res_g = rr_spec_analysis(datadict=datadict, path=path, **kwargs)

        datadict["metadata"]["schema"] = schema_e
        anal_res_e = rr_spec_analysis(datadict=datadict, path=path, **kwargs)

        sqil.set_plot_style(plt)
        # fig, ax = plt.subplots(1,1)
        # ax.plot()

        fr_g = anal_res_g.updated_params.get("q0", {}).get(
            "readout_resonator_frequency", None
        )
        fr_e = anal_res_e.updated_params.get("q0", {}).get(
            "readout_resonator_frequency", None
        )

        if fr_g and fr_e:
            print(fr_e - fr_g)

        return
