"""This module defines the spin locking experiment.

The spin locking experiment has the following pulse sequence:

    qb --- [ prep transition ] --- [ x90_transition ] --- [ ry(delay) ] ---
    --- [ x90_transition ] --- [ measure ]

If multiple qubits are passed to the `run` workflow, the above pulses are applied
in parallel on all the qubits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import matplotlib.pyplot as plt
import numpy as np
import sqil_core.fit as fit
from laboneq.dsl.enums import AcquisitionType, AveragingMode
from laboneq.simple import Experiment, SweepParameter, dsl
from laboneq.workflow import option_field
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import TuneupExperimentOptions
from sqil_core.experiment import AnalysisResult, ExperimentHandler, multi_qubit_handler
from sqil_core.utils import *

if TYPE_CHECKING:
    from laboneq.dsl.quantum.qpu import QPU
    from laboneq_applications.typing import QuantumElements, QubitSweepPoints


class SpinLockingOptions(TuneupExperimentOptions):
    """Base options for the resonator spectroscopy experiment.

    Additional attributes:
        refocus_pulse:
            String to define the quantum operation in-between the x90 pulses.
            Default: "y180".
    """

    # FIXME: not used
    pulse: dict = attrs.field(
        factory=lambda: {
            "function": "gaussian_square_sqil",
            "can_compress": True,
        }
    )
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
    qubits: QuantumElements,
    lengths: QubitSweepPoints,
    rel_amp: float | None = None,
    options: SpinLockingOptions | None = None,
    transition="ge",
    use_helper_drive=False,
) -> Experiment:
    """Creates a spin locking Experiment.

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on. May be either a single
            qubit or a list of qubits.
        lengths:
            The delays to sweep over for each qubit. Note that `delays` must be
            identical for qubits that use the same measure port.
        rel_amp:
            The relative amplitude specifies the spin_locking pulse amplitude
            relative to the pi-pulse amplitude. Default is None and corresponds to
            the pi pulse amplitude of the specified transition.
        options:
            The options for building the experiment.
            See [EchoExperimentOptions] and [BaseExperimentOptions] for
            accepted options.
            Overwrites the options from [TuneupExperimentOptions] and
            [BaseExperimentOptions].

    Returns:
        experiment:
            The generated LabOne Q experiment instance to be compiled and executed.

    Raises:
        ValueError:
            If delays is not a list of numbers or array when a single qubit is passed.

    Example:
        ```python
        options = {
            "count": 10,
            "transition": "ge",
            "averaging_mode": "cyclic",
            "acquisition_type": "integration_trigger",
            "cal_traces": True,
        }
        options = TuneupExperimentOptions(**options)
        setup = DeviceSetup()
        qpu = QPU(
            setup=DeviceSetup("my_device"),
            qubits=[TunableTransmonQubit("q0"), TunableTransmonQubit("q1")],
            quantum_operations=TunableTransmonOperations(),
        )
        temp_qubits = qpu.copy_qubits()
        create_experiment(
            qpu=qpu,
            qubits=temp_qubits,
            lengths=[[1e-6, 5e-6, 10e-6], [1e-6, 5e-6, 10e-6]]
            options=options,
        )
        ```
    """
    # Define the custom options for the experiment
    opts = SpinLockingOptions() if options is None else options
    qubits, lengths = validation.validate_and_convert_qubits_sweeps(qubits, lengths)
    angle = rel_amp * np.pi if rel_amp is not None else np.pi

    opts.transition = transition

    qop = qpu.quantum_operations
    with dsl.acquire_loop_rt(
        count=opts.count,
        averaging_mode=opts.averaging_mode,
        acquisition_type=opts.acquisition_type,
        repetition_mode=opts.repetition_mode,
        repetition_time=opts.repetition_time,
        reset_oscillator_phase=opts.reset_oscillator_phase,
    ):
        for q, q_lengths in zip(qubits, lengths, strict=False):
            with dsl.sweep(
                name=f"length_{q.uid}",
                parameter=SweepParameter(f"length_{q.uid}", q_lengths),
            ) as length:
                qop.prepare_state(q, opts.transition[0])
                qop.x90(q, opts.transition)
                qop.ry(
                    q,
                    angle=angle,
                    transition="helper" if use_helper_drive else opts.transition,
                    length=length,
                    # pulse=opts.pulse,
                )
                qop.x90(q, opts.transition)
                qop.measure(q, dsl.handles.result_handle(q.uid))
                qop.passive_reset(q)
            if opts.use_cal_traces:
                with dsl.section(
                    name=f"cal_{q.uid}",
                ):
                    for state in opts.cal_states:
                        qop.prepare_state(q, state)
                        qop.measure(
                            q,
                            dsl.handles.calibration_trace_handle(q.uid, state),
                        )
                        qop.passive_reset(q)


class SpinLocking(ExperimentHandler):
    exp_name = "spin_locking"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "pulse_lengths": {"role": "x-axis", "unit": "s", "scale": 1e9},
    }

    def sequence(
        self,
        pulse_lengths,
        qu_ids=["q0"],
        transition="ge",
        use_helper_drive=False,
        options: SpinLockingOptions | None = None,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(
            self.qpu,
            qubits[0],
            pulse_lengths[0],
            transition=transition,
            use_helper_drive=use_helper_drive,
            options=options,
        )

    def analyze(self, path, *args, **kwargs):
        return analyze_spin_echo(path=path, **kwargs)


@multi_qubit_handler
def analyze_spin_echo(
    datadict,
    qpu=None,
    qu_id="q0",
    transition="ge",
    relevant_params=None,
    fit_kwargs=None,
    **kwargs,
):
    # Prepare analysis result object
    anal_res = AnalysisResult()

    if fit_kwargs is None:
        fit_kwargs = {}

    # Extract data and metadata
    qu_data, qu_info, datadict = get_data_and_info(datadict=datadict)
    lengths, y_data, sweeps = qu_data
    x_info, y_info, sweep_info = qu_info

    fit_res, fig = None, None
    qubit_params = enrich_qubit_params(qpu[qu_id]) if qpu else {}

    # Set plot style
    set_plot_style(plt)

    has_sweeps = y_data.ndim > 1
    if not has_sweeps:
        try:
            # Project the data and start plot
            proj, inv = fit.transform_data(y_data, inv_transform=True)
            fig, axs = plot_projection_IQ(datadict=datadict, proj_data=proj)
            anal_res.add_figure(fig, "fig", qu_id)

            # Analyze
            fit_res = fit.fit_decaying_exp(lengths, proj, **fit_kwargs)

            anal_res.add_fit(fit_res, "Decaying oscillations", qu_id)
            # Update parameters
            anal_res.add_params(
                {f"decay": fit_res.params_by_name["tau"]},
                qu_id,
            )

            x_fit = np.linspace(lengths[0], lengths[-1], 10 * len(lengths))
            inverse_fit = inv(fit_res.predict(x_fit))

            # Plot the fit
            axs[0].plot(
                x_fit * x_info.scale,
                fit_res.predict(x_fit) * y_info.scale,
                "tab:red",
                alpha=0.8,
                linewidth=2,
            )
            axs[1].plot(
                inverse_fit.real * y_info.scale,
                inverse_fit.imag * y_info.scale,
                "tab:red",
            )

        except Exception as e:
            print("Error while fitting projected data", e)

    elif has_sweeps:
        fig, axs = plot_mag_phase(datadict=datadict, raw=True)
        anal_res.add_figure(fig, "fig", qu_id)

    finalize_plot(
        fig,
        f"Spin locking ({transition})",
        qu_id,
        fit_res,
        qubit_params,
        anal_res.updated_params.get(qu_id, {}),
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    return anal_res
