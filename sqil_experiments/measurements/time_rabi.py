import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from laboneq.simple import (
    Experiment,
    SectionAlignment,
    SweepParameter,
    dsl,
    pulse_library,
)
from laboneq.workflow import option_field, task_options
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from matplotlib.gridspec import GridSpec
from numpy.typing import ArrayLike
from sqil_core.experiment import ExperimentHandler


@task_options(base_class=BaseExperimentOptions)
class TimeRabiOptions:
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
    options: TimeRabiOptions | None = None,
) -> Experiment:
    opts = TimeRabiOptions() if options is None else options
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
                    pulse={"can_compress": True, "width": pulse_len},
                )
            with dsl.section(name="measure", alignment=SectionAlignment.LEFT):
                qop.measure(qubit, dsl.handles.result_handle(qubit.uid))
                qop.passive_reset(qubit)


class TimeRabi(ExperimentHandler):
    exp_name = "time_rabi"
    db_schema = {
        "data": {"type": "data"},
        "pulse_lengths": {"type": "axis", "plot": "x", "unit": "s"},
    }

    def sequence(
        self,
        pulse_lengths,
        qu_idx=0,
        options: TimeRabiOptions | None = None,
        *params,
        **kwargs,
    ):
        return create_experiment(
            self.qpu,
            self.qpu.qubits[qu_idx],
            pulse_lengths,
            options=options,
        )

    def analyze(self, path, *params, **kwargs):
        # Read data
        data, lengths, sweep = sqil.extract_h5_data(
            path, ["data", "pulse_lengths", "sweep0"]
        )

        # Analyze data
        proj, inv = sqil.fit.transform_data(data, inv_transform=True)
        fit_res = sqil.fit.fit_decaying_oscillations(lengths, proj)
        x_fit = np.linspace(lengths[0], lengths[-1], 3 * len(lengths))
        inverse_fit = inv(fit_res.predict(x_fit))

        # Make parameters pretty
        omega_r = sqil.format_number(1 / fit_res.params[4], unit="Hz")
        t_pi = sqil.format_number(fit_res.metadata["pi_time"], unit="s")
        tau = sqil.format_number(fit_res.params[1], unit="s")

        sqil.set_plot_style(plt)
        fig = plt.figure(figsize=(20, 7), constrained_layout=True)
        gs = GridSpec(nrows=1, ncols=10, figure=fig, wspace=0.2)

        # Plot the projection
        ax_proj = fig.add_subplot(gs[:, :6])  # 6/10 width
        ax_proj.plot(lengths * 1e6, np.real(proj) * 1e3, "o")
        ax_proj.plot(x_fit * 1e6, fit_res.predict(x_fit) * 1e3, "tab:red")
        ax_proj.set_xlabel(r"Time [$\mu$s]")
        ax_proj.set_ylabel("Projection [mV]")
        ax_proj.set_title(
            rf"$t_\pi = ${t_pi}  |  $\Omega_R = ${omega_r}  |  $\tau =${tau}"
        )

        # Plot IQ data
        ax_iq = fig.add_subplot(gs[:, 6:])  # 4/10 width
        ax_iq.scatter(0, 0, marker="+", color="black", s=150)
        ax_iq.plot(data.real * 1e3, data.imag * 1e3, "o")
        ax_iq.plot(inverse_fit.real * 1e3, inverse_fit.imag * 1e3, "tab:red")
        ax_iq.set_xlabel("In-Phase [mV]")
        ax_iq.set_ylabel("Quadrature [mV]")
        ax_iq.set_aspect(aspect="equal", adjustable="datalim")

        fig.suptitle("Time Rabi")

        fig.savefig(f"{path}/time_rabi.png")

        return fit_res.summary()
