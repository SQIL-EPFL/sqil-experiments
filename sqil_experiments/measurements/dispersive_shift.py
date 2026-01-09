import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from laboneq.simple import Experiment, SectionAlignment, SweepParameter, dsl
from laboneq.workflow import option_field, task_options
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from numpy.typing import ArrayLike
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

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
        },
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
        return analyze_dispersive_shift(path=path, **kwargs)


@multi_qubit_handler
def analyze_dispersive_shift(
    datadict,
    qu_id="q0",
    transition="ge",
    qpu=None,
    at_sweep_idx=None,
    relevant_params=[],
    **kwargs,
) -> AnalysisResult:
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    x_data, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res = None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    # Set plot style
    set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        schema_g = {**datadict["metadata"]["schema"]}
        schema_e = {**datadict["metadata"]["schema"]}

        del schema_g["data_e"]
        del schema_e["data_g"]

        datadict["metadata"]["schema"] = schema_g
        anal_res_g = rr_spec_analysis(datadict=datadict, qpu=qpu, qu_id=qu_id)

        datadict["metadata"]["schema"] = schema_e
        anal_res_e = rr_spec_analysis(datadict=datadict, qpu=qpu, qu_id=qu_id)

        # Extract resonance frequencies
        fr_g = anal_res_g.updated_params.get("q0", {}).get(
            "readout_resonator_frequency", None
        )
        fr_e = anal_res_e.updated_params.get("q0", {}).get(
            "readout_resonator_frequency", None
        )
        # Add fits to new result
        for key, fit in anal_res_g.fits.items():
            anal_res.add_fit(fit, f"g_{key}", qu_id)
        for key, fit in anal_res_e.fits.items():
            anal_res.add_fit(fit, f"e_{key}", qu_id)

        # Compute chi
        chi = np.nan
        if fr_g and fr_e:
            chi = fr_e - fr_g
            anal_res.add_params({f"{transition}_chi_shift": chi}, qu_id)

        # Plotting
        # Grab all Line2D objects from ax1 and ax2
        g_lines = anal_res_g.figures["q0_fig"].axes[1].get_lines()
        e_lines = anal_res_e.figures["q0_fig"].axes[1].get_lines()
        # Extract x and y labels
        x_label = anal_res_g.figures["q0_fig"].axes[2].get_xlabel()
        y_label = anal_res_g.figures["q0_fig"].axes[1].get_ylabel()
        # Close figures
        plt.close("all")

        # Create new figure and add both lines
        fig, ax = plt.subplots(1, 1)
        anal_res.add_figure(fig, "fig", qu_id)
        for lines, lab in zip([g_lines, e_lines], ["g", "e"]):
            ax.plot(lines[0].get_xdata(), lines[0].get_ydata(), "o", label=lab)
            ax.plot(lines[1].get_xdata(), lines[1].get_ydata(), color="tab:red")

        # Draw two vertical lines
        x1, x2 = fr_g * 1e-9, fr_e * 1e-9
        ax.axvline(x=x1, color="tab:blue", linestyle="--")
        ax.axvline(x=x2, color="tab:orange", linestyle="--")
        # Draw the arrow with two heads (symbolizing distance between lines)
        arrow = patches.FancyArrowPatch(
            (x1, 0),  # Start point (x1, 0)
            (x2, 0),  # End point (x2, 0)
            arrowstyle="<|-|>",  # Arrow style with two heads
            mutation_scale=20,  # Size of the arrows
            color="black",
            linewidth=2,
        )
        # Add the arrow to the plot
        ax.add_patch(arrow)
        # Add text above the arrow
        midpoint_x = (x1 + x2) / 2  # Find the midpoint of the x-coordinates
        ax.text(midpoint_x, 0.005, r"$\chi$", ha="center", va="bottom")

        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.legend()
    else:
        fig, axs = plot_mag_phase(datadict=datadict, raw=True)
        anal_res.add_figure(fig, "fig", qu_id)

    finalize_plot(
        fig,
        f"Dispersive shift ({transition})",
        qu_id,
        fit_res,
        qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
