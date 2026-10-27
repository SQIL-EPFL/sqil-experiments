from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from laboneq.simple import Experiment, SectionAlignment, dsl
from laboneq_applications.core import validation
from sqil_core.experiment import AnalysisResult
from sqil_core.utils import extract_h5_data, plot_IQ_ellipse, set_plot_style

from sqil_experiments.measurements.iq_blobs import IQBlobs, IQBlobsOptions

if TYPE_CHECKING:
    from collections.abc import Sequence

    from laboneq.dsl.quantum.qpu import QPU
    from laboneq_applications.typing import QuantumElements


@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    initial_states: Sequence[str],
    options: IQBlobsOptions | None = None,
) -> Experiment:
    # Define the custom options for the experiment
    opts = IQBlobsOptions() if options is None else options
    qubits = validation.validate_and_convert_qubits_sweeps(qubits)

    qop = qpu.quantum_operations
    with dsl.acquire_loop_rt(
        count=opts.count,
        averaging_mode=opts.averaging_mode,
        acquisition_type=opts.acquisition_type,
        repetition_mode=opts.repetition_mode,
        repetition_time=opts.repetition_time,
        reset_oscillator_phase=opts.reset_oscillator_phase,
    ):
        for s0 in initial_states:
            # Herald: find out in which state the qubit starts
            with dsl.section(name="Herald", alignment=SectionAlignment.LEFT):
                for q in qubits:
                    qop.measure(q, dsl.handles.result_handle(f"{q.uid}/herald_{s0}"))
                    qop.passive_reset(q)

            with dsl.section(
                name="State preparation",
                alignment=SectionAlignment.RIGHT,
            ):
                for q in qubits:
                    qop.prepare_state.omit_section(q, s0)

            with dsl.section(name="Measure", alignment=SectionAlignment.LEFT):
                for q in qubits:
                    qop.measure(q, dsl.handles.result_handle(f"{q.uid}/{s0}"))
                    qop.passive_reset(q)


class IQBlobsHerald(IQBlobs):
    exp_name = "iq_blobs_herald"

    # Direction g -> e in the IQ plane [rad], one per qubit, e.g. {"q0": 1.93}.
    # Only used as a starting guess (it fixes which blob is g): the exact
    # direction and threshold are found from the herald data.
    theta_guess: dict = {}

    def on_before_experiment(self, *args, **kwargs):
        # Andrea's schema (one entry per state), plus one entry per herald
        super().on_before_experiment(*args, **kwargs)
        initial_states = self.run_args[0][0]
        for s in initial_states:
            self.db_schema.update(
                {f"herald_{s}": {"role": "data", "unit": "V", "scale": 1e3}}
            )

    def sequence(
        self,
        initial_states,
        qu_ids=["q0"],
        options: IQBlobsOptions | None = None,
        *params,
        **kwargs,
    ):
        qubits = [self.qpu[qu_id] for qu_id in qu_ids]
        return create_experiment(self.qpu, qubits, initial_states, options=options)

    def analyze(self, path, *args, **kwargs):
        qu_ids = kwargs.get("qu_ids", ["q0"])
        return analyze_iq_blobs_herald(path, qu_ids, self.theta_guess)


def find_g_e_blobs(shots, theta_guess=None, n_iter=50):
    """Split the shots (complex) into the g and e blobs.

    Returns theta, the direction g -> e in the IQ plane, and the threshold
    along that direction: rotated by exp(-1j * theta), g is below the
    threshold and e above.
    """
    if theta_guess is None:
        # No guess: main axis of the cloud (g and e may come out swapped)
        x, y = shots.real - shots.real.mean(), shots.imag - shots.imag.mean()
        _, v = np.linalg.eigh(np.cov(x, y))
        theta_guess = np.arctan2(v[1, -1], v[0, -1])

    theta = theta_guess
    proj = (shots * np.exp(-1j * theta)).real
    threshold = np.median(proj)
    for _ in range(n_iter):
        g = shots[proj < threshold].mean()  # centre of the g blob
        e = shots[proj >= threshold].mean()  # centre of the e blob
        theta = np.angle(e - g)
        proj = (shots * np.exp(-1j * theta)).real
        threshold = ((g + e) / 2 * np.exp(-1j * theta)).real
    return theta, threshold


def analyze_iq_blobs_herald(path, qu_ids=["q0"], theta_guess={}):
    anal_res = AnalysisResult()
    data = extract_h5_data(path)
    set_plot_style(plt)
    colors = {"g": "tab:blue", "e": "tab:orange", "f": "tab:green"}

    for qu_id in qu_ids:
        d = data[qu_id]
        states = [k.removeprefix("herald_") for k in d if k.startswith("herald_")]
        states.sort(key="gef".find)  # g first
        herald = {s: np.ravel(d[f"herald_{s}"]).astype(complex) for s in states}
        meas = {s: np.ravel(d[s]).astype(complex) for s in states}

        # g/e boundary from all the herald shots (about half g, half e)
        all_heralds = np.concatenate(list(herald.values()))
        theta, threshold = find_g_e_blobs(all_heralds, theta_guess.get(qu_id))
        rot = np.exp(-1j * theta)

        fig, axs = plt.subplots(1, 3, figsize=(20, 6))
        axs[0].hist(1e3 * (all_heralds * rot).real, bins=150, color="gray")
        out = {"theta": float(theta), "threshold": float(threshold)}
        print(f"{qu_id}: theta = {theta:.4f} rad, threshold = {threshold:.5g}")

        for s in states:
            h, m = herald[s] * rot, meas[s] * rot
            keep = h.real < threshold  # herald found the qubit in g
            p_e_all = np.mean(m.real > threshold)
            p_e_kept = np.mean(m[keep].real > threshold)
            out[s] = {
                "kept": float(keep.mean()),
                "P_e_all": float(p_e_all),
                "P_e_heralded": float(p_e_kept),
            }
            print(
                f"  {s}: kept {keep.mean():.2f} of the shots | "
                f"P(e) all = {p_e_all:.3f} | P(e) heralded = {p_e_kept:.3f}"
            )

            axs[1].scatter(1e3 * m.real, 1e3 * m.imag, s=1, alpha=0.1, color=colors[s])
            axs[2].scatter(
                1e3 * m[keep].real, 1e3 * m[keep].imag, s=1, alpha=0.1, color=colors[s]
            )
            plot_IQ_ellipse(1e3 * m[keep], axs[2], color=colors[s], label=s, conf=0.99)

        if "g" in out and "e" in out:
            fidelity = 1 - (out["g"]["P_e_heralded"] + 1 - out["e"]["P_e_heralded"]) / 2
            out["fidelity_heralded"] = float(fidelity)
            print(f"  readout fidelity (heralded) = {fidelity:.3f}")

        axs[0].set_title("herald shots")
        axs[0].set_xlabel("I rotated [mV]")
        axs[0].set_ylabel("counts")
        axs[1].set_title("all shots")
        axs[2].set_title("heralded shots (started in g)")
        for ax in axs:
            ax.axvline(1e3 * threshold, color="red")
        for ax in axs[1:]:
            ax.set_xlabel("I rotated [mV]")
            ax.set_ylabel("Q rotated [mV]")
            ax.set_aspect("equal")
            ax.grid(True)
        axs[2].legend()
        fig.suptitle(f"IQ blobs with heralding - {qu_id}")

        anal_res.add_figure(fig, "fig", qu_id)
        anal_res.add_output(out, qu_id)

    return anal_res
