from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import sqil_core.fit as fit
from laboneq.dsl.enums import AveragingMode
from laboneq.dsl.quantum import QPU
from laboneq.simple import (
    Experiment,
    LinearSweepParameter,
    SectionAlignment,
    SweepParameter,
    dsl,
)
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import TuneupExperimentOptions
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

if TYPE_CHECKING:
    from laboneq.dsl.quantum.qpu import QPU
    from laboneq_applications.typing import QuantumElements, QubitSweepPoints


def allxy_sequences(
    seq_ind, qop, qubits: QuantumElements, transition="ge", use_only_halfpi=False
):
    # use_only_halfpi=param_dict["use_only_halfpi"]
    # use_only_minus=param_dict[exp_name]["_use_only_minus"]

    # idle_gate = pulses["idle_gate"]
    # x_half_pi = pulses["m_x_half_pi"] if use_only_minus else pulses["x_half_pi"]
    # y_half_pi = pulses["m_y_half_pi"] if use_only_minus else pulses["y_half_pi"]
    # if not use_only_halfpi:
    #     x_pi = pulses["m_x_pi"] if use_only_minus else pulses["x_pi"]
    #     y_pi = pulses["m_y_pi"] if use_only_minus else pulses["y_pi"]

    for q in qubits:
        gate_t = getattr(q.parameters, f"{transition}_drive_length")

        with dsl.match(sweep_parameter=seq_ind):
            with dsl.case(0):  # Id+Id
                qop.delay(q=q, time=gate_t)
                qop.delay(q=q, time=gate_t)
            with dsl.case(1):  # Xpi+Xpi
                if use_only_halfpi:
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                else:
                    qop.x180(q=q, transition=transition)
                    qop.x180(q=q, transition=transition)
            with dsl.case(2):  # Ypi+Ypi
                if use_only_halfpi:
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                else:
                    qop.y180(q=q, transition=transition)
                    qop.y180(q=q, transition=transition)

            with dsl.case(3):  # Xpi+Ypi
                if use_only_halfpi:
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                else:
                    qop.x180(q=q, transition=transition)
                    qop.y180(q=q, transition=transition)

            with dsl.case(4):  # Ypi+Xpi
                if use_only_halfpi:
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                else:
                    qop.y180(q=q, transition=transition)
                    qop.x180(q=q, transition=transition)

            with dsl.case(5):  # Xpi/2+Id
                qop.x90(q=q, transition=transition)
                qop.delay(q=q, time=gate_t)
            with dsl.case(6):  # Ypi/2+Id
                qop.y90(q=q, transition=transition)
                qop.delay(q=q, time=gate_t)
            with dsl.case(7):  # Xpi/2+Ypi/2
                qop.x90(q=q, transition=transition)
                qop.y90(q=q, transition=transition)
            with dsl.case(8):  # Ypi/2+Xpi/2
                qop.y90(q=q, transition=transition)
                qop.x90(q=q, transition=transition)
            with dsl.case(9):  # Xpi/2+Ypi
                qop.x90(q=q, transition=transition)
                if use_only_halfpi:
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                else:
                    qop.y180(q=q, transition=transition)
            with dsl.case(10):  # Ypi/2+Xpi
                qop.y90(q=q, transition=transition)
                if use_only_halfpi:
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                else:
                    qop.x180(q=q, transition=transition)
            with dsl.case(11):  # Xpi+Ypi/2
                if use_only_halfpi:
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                else:
                    qop.x180(q=q, transition=transition)
                qop.y90(q=q, transition=transition)
            with dsl.case(12):  # Ypi+Xpi/2
                if use_only_halfpi:
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                else:
                    qop.y180(q=q, transition=transition)
                qop.x90(q=q, transition=transition)
            with dsl.case(13):  # Xpi/2+Xpi
                qop.x90(q=q, transition=transition)
                if use_only_halfpi:
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                else:
                    qop.x180(q=q, transition=transition)
            with dsl.case(14):  # Xpi+Xpi/2
                if use_only_halfpi:
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                else:
                    qop.x180(q=q, transition=transition)
                qop.x90(q=q, transition=transition)
            with dsl.case(15):  # Ypi/2+Ypi
                qop.y90(q=q, transition=transition)
                if use_only_halfpi:
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                else:
                    qop.y180(q=q, transition=transition)
            with dsl.case(16):  # Ypi+Ypi/2
                if use_only_halfpi:
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                else:
                    qop.y180(q=q, transition=transition)
                qop.y90(q=q, transition=transition)
            with dsl.case(17):  # Xpi+Id
                if use_only_halfpi:
                    qop.x90(q=q, transition=transition)
                    qop.x90(q=q, transition=transition)
                else:
                    qop.x180(q=q, transition=transition)
                qop.delay(q=q, time=gate_t)
            with dsl.case(18):  # Ypi+Id
                if use_only_halfpi:
                    qop.y90(q=q, transition=transition)
                    qop.y90(q=q, transition=transition)
                else:
                    qop.y180(q=q, transition=transition)
                qop.delay(q=q, time=gate_t)
            with dsl.case(19):  # Xpi/2+Xpi/2
                qop.x90(q=q, transition=transition)
                qop.x90(q=q, transition=transition)
            with dsl.case(20):  # Ypi/2+Ypi/2
                qop.y90(q=q, transition=transition)
                qop.y90(q=q, transition=transition)


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    options: TuneupExperimentOptions | None = None,
    transition="ge",
) -> Experiment:
    # Define the custom options for the experiment
    opts = TuneupExperimentOptions() if options is None else options

    xy_indices = LinearSweepParameter(uid="all_xy_sweep", start=0, stop=20, count=21)

    # We will fix the length of the measure section to the longest section among
    # the qubits to allow the qubits to have different readout and/or
    # integration lengths.
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

        with dsl.sweep(
            name="all_xy_sweep",
            parameter=xy_indices,
        ) as xy_idx:
            if opts.active_reset:
                qop.reset(
                    qubits,
                    # active_reset_states=opts.active_reset_states,
                    number_resets=opts.active_reset_repetitions,
                    # measure_section_length=max_measure_section_length,
                )

            with dsl.section(name="main", alignment=SectionAlignment.RIGHT):
                with dsl.section(
                    name="main_drive",
                    alignment=SectionAlignment.RIGHT,
                ):
                    allxy_sequences(xy_idx, qop, qubits, transition=transition)

            with dsl.section(name="measure", alignment=SectionAlignment.LEFT):
                for q in qubits:
                    sec = qop.measure(q, dsl.handles.result_handle(q.uid))
                    # Fix the length of the measure section
                    sec.length = max_measure_section_length
                    qop.passive_reset(q)


class AllXY(ExperimentHandler):
    exp_name = "allXY"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        # "time": {"role": "x-axis", "unit": "s", "scale": 1e6},
    }

    def sequence(self, qu_ids=0, options=None, transition="ge", *args, **kwargs):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(
            self.qpu, qubits, transition=transition, options=options
        )

    def analyze(self, path, *args, **kwargs):
        return analyze_allXY(path=path, **kwargs)


allxy_labels = [
    "II",
    "XX",
    "YY",
    "XY",
    "YX",
    "X/2 I",
    "Y/2 I",
    "X/2 Y/2",
    "Y/2 X/2",
    "X/2 Y",
    "Y/2 X",
    "X Y/2",
    "Y X/2",
    "X/2 X",
    "X X/2",
    "Y/2 Y",
    "Y Y/2",
    "X I",
    "Y I",
    "X/2 X/2",
    "Y/2 Y/2",
]


@multi_qubit_handler
def analyze_allXY(
    datadict, qpu=None, qu_id="q0", transition="ge", relevant_params=None, **kwargs
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    x_data, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    if relevant_params is None:
        relevant_params = [f"{transition}_drive_amplitude_pi"]

    # Set plot style
    set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        fig, axs = make_plot_frame("IQ")
        anal_res.add_figure(fig, "fig", qu_id)

        proj = fit.transform_data(y_data)
        proj_norm = (proj - np.min(proj)) / (np.max(proj) - np.min(proj))
        # Make sure it start in 0 and ends in 1
        start_mean = np.mean(proj_norm[:5])
        end_mean = np.mean(proj_norm[-4:])
        # flip if the start is larger than the end
        if start_mean > end_mean:
            proj_norm = 1 - proj_norm

        # Ideal AllXY levels
        axs[0].hlines(
            y=0.0,
            xmin=-0.5,
            xmax=4.5,
            color="tab:green",
            linestyle="--",
            linewidth=2,
            alpha=0.5,
        )
        axs[0].hlines(
            y=0.5,
            xmin=4.5,
            xmax=16.5,
            color="tab:green",
            linestyle="--",
            linewidth=2,
            alpha=0.5,
        )
        axs[0].hlines(
            y=1.0,
            xmin=16.5,
            xmax=20.5,
            color="tab:green",
            linestyle="--",
            linewidth=2,
            alpha=0.5,
        )
        # Data
        axs[0].plot(allxy_labels, proj_norm, "o")
        axs[1].plot(y_data.real * y_info.scale, y_data.imag * y_info.scale, "o")

        # Plot misc
        axs[0].set_xticks(np.arange(len(allxy_labels)))
        axs[0].set_xticklabels(allxy_labels, rotation=45, ha="right")
        axs[0].set_ylabel("Normalized projection")

        y_unit = f" [{y_info.rescaled_unit}]" if y_info.unit else ""
        axs[1].set_xlabel("In-Phase" + y_unit)
        axs[1].set_ylabel("Quadrature" + y_unit)
    else:
        fig, axs = make_plot_frame("IQ")
        anal_res.add_figure(fig, "fig", qu_id)

        proj = fit.transform_data(y_data)
        proj_norm = (proj - np.min(proj)) / (np.max(proj) - np.min(proj))
        # Make sure it start in 0 and ends in 1
        start_mean = np.mean(proj_norm[:, :5])
        end_mean = np.mean(proj_norm[:, -4:])
        # flip if the start is larger than the end
        if start_mean > end_mean:
            proj_norm = 1 - proj_norm
        # Compute the error
        target = np.concatenate([np.zeros(6), 0.5 * np.ones(11), np.ones(4)])
        err = np.abs(proj_norm - target)

        cmap = plt.cm.RdYlGn_r
        mesh = axs[0].pcolormesh(
            allxy_labels,
            sweeps[0] * sweep_info[0].scale,
            err,
            cmap=cmap,
            vmin=0,
            vmax=1,
            shading="auto",
        )
        fig.colorbar(mesh, ax=axs[0], label="Error")

        axs[1].plot(y_data.real, y_data.imag, "o", alpha=0.5)

        axs[0].set_xticks(np.arange(len(allxy_labels)))
        axs[0].set_xticklabels(allxy_labels, rotation=45, ha="right")
        axs[0].set_ylabel(sweep_info[0].name_and_unit)

        y_unit = f" [{y_info.rescaled_unit}]" if y_info.unit else ""
        axs[1].set_xlabel("In-Phase" + y_unit)
        axs[1].set_ylabel("Quadrature" + y_unit)

        fig2, ax = plt.subplots(1, 1)
        anal_res.add_figure(fig2, "fig2", qu_id)
        ax.plot(sweeps[0] * sweep_info[0].scale, np.mean(err, axis=1))
        ax.set_xlabel(sweep_info[0].name_and_unit)
        ax.set_ylabel("Error")

        finalize_plot(
            fig2,
            f"All XY ({transition})",
            qu_id,
            fit_res,
            qubit_params,
            updated_params=anal_res.updated_params.get(qu_id, {}),
            sweep_info=sweep_info,
            relevant_params=relevant_params,
        )

    finalize_plot(
        fig,
        f"All XY ({transition})",
        qu_id,
        fit_res,
        qubit_params,
        updated_params=anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
