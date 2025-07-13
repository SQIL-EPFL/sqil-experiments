import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from helpers.plottr import DataDict, DDH5Writer
from helpers.sqil_transmon.operations import SqilTransmonOperations
from helpers.sqil_transmon.qubit import SqilTransmon
from laboneq.dsl.enums import AcquisitionType, AveragingMode

# from rr_spec import create_experiment
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from laboneq.simple import Experiment, SweepParameter, dsl
from laboneq.workflow import option_field, task_options, workflow_options
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import BaseExperimentOptions
from laboneq_applications.qpu_types.tunable_transmon import (
    TunableTransmonOperations,
    TunableTransmonQubit,
)
from numpy.typing import ArrayLike
from sqil_core.experiment import ExperimentHandler


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
        "data": {"role": "data", "unit": "V", "scale": 1e3},
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
        qu_idx=0,
        options: ResonatorSpectroscopyExperimentOptions | None = None,
        *params,
        **kwargs,
    ):
        return create_experiment(
            self.qpu,
            self.qpu.quantum_elements[qu_idx],
            readout_resonator_frequency,
            options=options,
        )

    def analyze(self, path, *args, **kwargs):
        # data, freq, sweep = sqil.extract_h5_data(
        #     path, ["data", "frequencies", "sweep0"]
        # )
        # options = kwargs.get("options", ResonatorSpectroscopyExperimentOptions())

        # result = None

        # if options.averaging_mode == AveragingMode.SINGLE_SHOT:
        #     fig, ax = plt.subplots(1, 1, figsize=(16, 5))
        #     linmag = np.abs(data[0])
        #     ax.errorbar(
        #         freq[0],
        #         np.mean(linmag, axis=0),
        #         np.std(linmag, axis=0),
        #         fmt="-o",
        #         color="tab:blue",
        #         label="Mean with Error",
        #         ecolor="tab:orange",
        #         capsize=5,
        #         capthick=2,
        #         elinewidth=2,
        #         markersize=5,
        #     )
        # else:
        #     is1D = np.array(data).ndim == 1
        #     if is1D:
        #         fig, ax = plt.subplots(1, 1)
        #         ax.plot(freq, np.abs(data))
        #     else:
        #         fig, ax = plt.subplots(1, 1)
        #         ax.pcolormesh(freq, sweep, np.abs(data))

        return rr_spec_analysis(path, *args, **kwargs)
        # fig.savefig(f"{path}/fig.png")


from sqil_core.experiment import AnalysisResult
from sqil_core.fit import FitQuality
from sqil_core.utils import *

# map_data_dict, extract_h5_data, param_info_from_schema, enrich_qubit_params, get_relevant_exp_parameters, plot_mag_phase, ONE_TONE_PARAMS, ParamInfo


def rr_spec_analysis(
    path=None,
    datadict=None,
    qpu=None,
    at_idx=None,
    relevant_params=ONE_TONE_PARAMS,
    qu_uid="q0",
    **kwargs,
) -> AnalysisResult:
    # Prepare analysis result object
    anal_res = AnalysisResult()
    anal_res.updated_params[qu_uid] = {}
    fit_res = None

    # Extract data and metadata
    all_data, all_info, datadict = get_data_and_info(path=path, datadict=datadict)
    x_data, y_data, sweeps = all_data
    x_info, y_info, sweep_info = all_info

    # Extract qubit parameters
    if qpu is None and path is not None:
        qpu = read_qpu(path, "qpu_old.json")
    qubit_params = {}
    if qpu is not None:
        qubit_params = enrich_qubit_params(qpu.quantum_element_by_uid(qu_uid))

    measurement = qubit_params["readout_configuration"].value

    # Check if data has sweeps
    has_sweeps = y_data.ndim > 1
    if at_idx is not None:
        has_sweeps = False
        x_data, y_data = x_data[at_idx], y_data[at_idx]
        all_data = x_data, y_data, sweeps
        qubit_params[sweep_info[0].id].value = sweeps[0][at_idx]

    # Rescale data
    x_data_scaled = x_data * x_info.scale
    y_data_scaled = y_data * y_info.scale

    sqil.set_plot_style(plt)
    if not has_sweeps:
        y_unit = y_info.unit

        # If dB convert to linear magnitude for the fit
        if y_unit == "dB":
            y_data = 10 ** (np.abs(y_data) / 20) * np.exp(1j * np.angle(y_data))
            all_data = (x_data, y_data, sweeps)
            y_unit = "V"
        y_unit_str = f" [{y_info.rescaled_unit}]" if y_unit else ""

        # Plot without fit
        fig, axs = sqil.resonator.plot_resonator(x_data_scaled, y_data_scaled)
        anal_res.figures.update({"fig": fig})
        # Fix axis names
        axs[0].set_xlabel("In-phase" + y_unit_str)
        axs[0].set_ylabel("Quadrature" + y_unit_str)
        axs[1].set_ylabel("Magnitude" + y_unit_str)
        axs[2].set_xlabel(x_info.name_and_unit)

        # Try complex model fit
        try:
            fit_res = analyze_rr_complex_data(
                anal_res, all_data, all_info, measurement, axs, qu_uid
            )
        except Exception as e:
            print(f"Error fitting the complex resonator data:", e)
            print(f"Trying to fit just the magnitude")
            # Fallback to linmag squared fit
            try:
                fit_res = analyze_rr_magnitude(
                    anal_res, all_data, all_info, axs, qu_uid
                )
            except Exception as e2:
                print(f"Error fitting the magnitude:", e2)
                fit_res = None
    elif has_sweeps:
        fig, axs = plot_mag_phase(datadict=datadict)
        anal_res.figures.update({"fig": fig})

        sweep0_info = sweep_info[0]
        if sweep0_info.id == "readout_amplitude":
            # Try to extract the optimal readout amplitude
            # If the optimal amplitude is found, run rr_spec_analysis on the chosen trace
            analyze_rr_amplitude_sweep(
                anal_res, all_data, all_info, datadict, qpu, axs, qu_uid
            )
            fit_res = None

    finalize_plot(
        fig,
        "Readout resonator spectroscopy",
        fit_res=fit_res,
        qubit_params=qubit_params,
        updated_params=anal_res.updated_params[qu_uid],
        sweep_info=sweep_info,
        relevant_params=relevant_params,
    )

    fig.tight_layout()
    # plt.show()

    return anal_res


# TODO: add power axis


def analyze_rr_complex_data(anal_res, all_data, all_info, measurement, axs, qu_uid):
    """Analyze the complex data to extract the resonance frequency and kappa_tot."""
    x_data, y_data, _ = all_data
    x_info, y_info, _ = all_info

    is_wide_range = x_data[-1] - x_data[0] > 200e6
    fit_acceptability = FitQuality.GOOD if is_wide_range else FitQuality.ACCEPTABLE
    # Quick resonator fit to get parameter guesses
    guess = sqil.resonator.quick_fit(x_data, y_data, measurement)
    # Full resonator fit
    fit_res = sqil.resonator.full_fit(x_data, y_data, measurement, *guess)
    if not fit_res.is_acceptable("nrmse", threshold=fit_acceptability):
        raise Exception(
            f"Fit not acceptable with {fit_res.model_name} model, nrmse = {fit_res.metrics['nrmse']:.4f}"
        )
    # Extract parameters
    fr = fit_res.params_by_name["fr"]
    anal_res.updated_params[qu_uid]["readout_resonator_frequency"] = fr
    anal_res.updated_params[qu_uid]["readout_kappa_tot"] = (
        fr / fit_res.params_by_name["Q_tot"]
    )
    anal_res.fits.update({"Complex fit": fit_res})
    # Plot
    x_fit = np.linspace(x_data[0], x_data[-1], np.max([2000, len(x_data)]))
    y_fit_scaled = fit_res.predict(x_fit) * y_info.scale
    # Make sure the fitted unwrapped phase is aligned with the data
    # If the data has a background it might gain a phase offset to the perfectly linear fit
    phase_offset = 0
    if is_wide_range:
        fr_idx_data = find_closest_index(x_data, fr)
        fr_idx_fit = find_closest_index(x_fit, fr)
        uphase = np.unwrap(np.angle(y_data * y_info.scale))
        ufit = np.unwrap(np.angle(y_fit_scaled))
        phase_offset = -ufit[fr_idx_fit] + uphase[fr_idx_data]
        # y_fit_scaled *= np.exp(1j * phase_offset)
    axs[0].plot(np.real(y_fit_scaled), np.imag(y_fit_scaled), color="tab:orange")
    axs[1].plot(x_fit * x_info.scale, np.abs(y_fit_scaled), color="tab:orange")
    axs[2].plot(
        x_fit * x_info.scale,
        np.unwrap(np.angle(y_fit_scaled)) + phase_offset,
        color="tab:orange",
    )
    return fit_res


def analyze_rr_magnitude(anal_res, all_data, all_info, axs, qu_uid):
    """Analyze the squared magnitude to extract the resonance frequency."""
    x_data, y_data, _ = all_data
    x_info, y_info, _ = all_info

    fit_res = sqil.resonator.linmag_fit(x_data, y_data)
    if not fit_res.is_acceptable("nrmse"):
        raise Exception(
            f"Fit not acceptable with {fit_res.model_name} model, nrmse = {fit_res.metrics['nrmse']:.4f}"
        )
    anal_res.updated_params[qu_uid]["readout_resonator_frequency"] = (
        fit_res.params_by_name["x0"]
    )
    anal_res.fits.update({"Magnitude squared fit": fit_res})
    # Plot
    x_fit = np.linspace(x_data[0], x_data[-1], np.max([2000, len(x_data)]))
    y_fit = np.sqrt(fit_res.predict(x_fit)) * np.max(np.abs(y_data))
    axs[1].plot(x_fit * x_info.scale, y_fit * y_info.scale, color="tab:orange")

    return fit_res


def analyze_rr_amplitude_sweep(
    anal_res, all_data, all_info, datadict, qpu, axs, qu_uid
):
    """Tries to find the optimal amplitude for readout. If the optimal amplitude is found,
    also the single trace at the chosen amplitude in analyzed recursively.

    The optimal amplitude is found by fitting the square magnitude with a lorentzian. If the sweep
    starts from low amplitudes, the NRMSE should initially decrease with amplitude (SNR is getting better),
    and then increase again (the resonator enters the non-linear regime). This function uses the earlies
    (lowest amplitude) dip in NRMSE to estimate the optimal amplitude. However, if the fit is
    not great, the result is discarded."""
    x_data, y_data, sweeps = all_data
    x_info, y_info, sweep_info = all_info
    sweep0_info = sweep_info[0]

    nrmses = np.ones(len(sweeps[0]))
    for i in range(len(sweeps[0])):
        fit_res = sqil.resonator.linmag_fit(x_data[i, :], y_data[i, :])
        nrmses[i] = fit_res.metrics["nrmse"]
    anal_res.extra_data.update({"nrmses": nrmses})
    best_idx = sqil.find_first_minima_idx(nrmses)

    is_fit_okay = False
    if best_idx is not None:
        quality = sqil.fit.evaluate_fit_quality(
            {"nrmse": nrmses[best_idx]}, recipe="nrmse"
        )
        is_fit_okay = quality >= FitQuality.GREAT

    # Plot NRMSE vs amplitude
    fig2, ax = plt.subplots(1, 1)
    ax.plot(sweeps[0], nrmses, ".-", ms=20, color="tab:blue", mfc="tab:blue")
    ax.axhline(
        sqil.fit.FIT_QUALITY_THRESHOLDS["nrmse"][0][0],
        label=f"Great fit",
        linestyle="--",
        color="tab:green",
    )
    ax.axhline(
        sqil.fit.FIT_QUALITY_THRESHOLDS["nrmse"][1][0],
        label=f"Good fit",
        linestyle="--",
        color="tab:olive",
    )
    ax.set_xlabel(sweep0_info.name_and_unit)
    ax.set_ylabel("NRMSE")
    ax.set_title("Magnitude squared fits")
    if is_fit_okay:
        ax.scatter(
            sweeps[0][best_idx],
            nrmses[best_idx],
            color="tab:red",
            zorder=3,
            s=400,
            marker="*",
            label=f"Selected {str(sweep0_info.name).lower()}",
        )
        axs[0].axhline(sweeps[0][best_idx], color="tab:red", linestyle="--")
    ax.legend()
    fig2.tight_layout()
    anal_res.figures.update({"fig_best_amp": fig2})

    # Recursive step to update readout frequency and kappa_tot
    if is_fit_okay:
        best_amp = sweeps[0][best_idx]
        anal_res.updated_params[qu_uid].update({sweep0_info.id: best_amp})
        try:
            anal_res_no_sweep = rr_spec_analysis(
                datadict=datadict, qpu=qpu, at_idx=best_idx
            )
            anal_res.fits.update(anal_res_no_sweep.fits)
            for qu_id in anal_res.updated_params.keys():
                anal_res.updated_params[qu_id].update(
                    anal_res_no_sweep.updated_params[qu_id]
                )
            fig_single = anal_res_no_sweep.figures["fig"]
            fig_single.suptitle(
                fig_single.get_suptitle().replace(
                    "resonator spectroscopy", "trace at chosen operating point"
                )
            )
            anal_res.figures.update({"fig single": fig_single})
        except Exception as e:
            anal_res.updated_params[qu_uid].update(
                {
                    "readout_resonator_frequency": fit_res.params_by_name["x0"],
                }
            )
            print("Error while analyzing the selected single trace", e)
