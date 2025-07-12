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
    path=None, datadict=None, qpu=None, at_idx=None, **kwargs
) -> AnalysisResult:
    anal_res = AnalysisResult()

    if path is None and datadict is None:
        raise Exception("At least one of `path` and `datadict` must be specified.")
    if path is not None:
        datadict = extract_h5_data(path, schema=True)
    schema = datadict["schema"]

    x_data, y_data, sweeps, datadict_map = map_data_dict(datadict)

    # Extract qubit parameters
    qubit_params = {}
    try:
        if qpu is None and path is not None:
            qpu = read_qpu(path, "qpu_old.json")
        qubit_params = enrich_qubit_params(qpu.quantum_elements[0])
    except Exception as e:
        print("Error reading QPU", e)
    measurement = qubit_params["readout_configuration"].value
    anal_res.updated_params["q0"] = {}
    fit_res = None

    if at_idx is not None:
        x_data, y_data = x_data[at_idx], y_data[at_idx]
        sweep_key = datadict_map["sweeps"][0]
        sweep0_info = param_info_from_schema(sweep_key, schema[sweep_key])
        qubit_params[sweep0_info.id].value = sweeps[0][at_idx]

    x_info = param_info_from_schema(
        datadict_map["x_data"], schema[datadict_map["x_data"]]
    )
    y_info = param_info_from_schema(
        datadict_map["y_data"], schema[datadict_map["y_data"]]
    )
    x_data_scaled = x_data * x_info.scale
    y_data_scaled = y_data * y_info.scale

    has_sweeps = y_data.ndim > 1

    if not has_sweeps:
        y_unit = y_info.unit
        y_scale = y_info.scale

        # If dB convert to linear magnitude for the fit
        if y_unit == "dB":
            y_data = 10 ** (np.abs(y_data) / 20) * np.exp(1j * np.angle(y_data))
            y_unit = "V"
        y_unit_str = f" [{y_info.rescaled_unit}]" if y_unit else ""

        # Plot without fit
        sqil.set_plot_style(plt)
        fig, axs = sqil.resonator.plot_resonator(x_data_scaled, y_data_scaled)
        anal_res.figures.update({"fig": fig})
        # Fix axis names
        axs[0].set_xlabel("In-phase" + y_unit_str)
        axs[0].set_ylabel("Quadrature" + y_unit_str)
        axs[1].set_ylabel("Magnitude" + y_unit_str)
        axs[2].set_xlabel(x_info.name_and_unit)

        # Fit data to extract parameters
        try:
            is_wide_range = x_data[-1] - x_data[0] > 200e6
            fit_acceptability = (
                FitQuality.GOOD if is_wide_range else FitQuality.ACCEPTABLE
            )
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
            anal_res.updated_params["q0"]["readout_resonator_frequency"] = fr
            anal_res.updated_params["q0"]["readout_kappa_tot"] = (
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
                uphase = np.unwrap(np.angle(y_data_scaled))
                ufit = np.unwrap(np.angle(y_fit_scaled))
                phase_offset = -ufit[fr_idx_fit] + uphase[fr_idx_data]
                # y_fit_scaled *= np.exp(1j * phase_offset)
            axs[0].plot(
                np.real(y_fit_scaled), np.imag(y_fit_scaled), color="tab:orange"
            )
            axs[1].plot(x_fit * x_info.scale, np.abs(y_fit_scaled), color="tab:orange")
            axs[2].plot(
                x_fit * x_info.scale,
                np.unwrap(np.angle(y_fit_scaled)) + phase_offset,
                color="tab:orange",
            )
        except Exception as e:
            print(f"Error fitting the complex resonator data:", e)
            print(f"Trying to fit just the magnitude")
            try:
                fit_res = sqil.resonator.linmag_fit(x_data, y_data)
                if not fit_res.is_acceptable("nrmse"):
                    raise Exception(
                        f"Fit not acceptable with {fit_res.model_name} model, nrmse = {fit_res.metrics['nrmse']:.4f}"
                    )
                anal_res.updated_params["q0"]["readout_resonator_frequency"] = (
                    fit_res.params_by_name["x0"]
                )
                anal_res.fits.update({"Magnitude squared fit": fit_res})
                # Plot
                x_fit = np.linspace(x_data[0], x_data[-1], np.max([2000, len(x_data)]))
                y_fit = np.sqrt(fit_res.predict(x_fit)) * np.max(np.abs(y_data))
                axs[1].plot(
                    x_fit * x_info.scale, y_fit * y_info.scale, color="tab:orange"
                )
            except Exception as e2:
                print(f"Error fitting the magnitude:", e2)
                fit_res = None
    else:
        fig, axs = plot_mag_phase(datadict=datadict)
        anal_res.figures.update({"fig": fig})

        sweep_key = datadict_map["sweeps"][0]
        sweep0_info = param_info_from_schema(sweep_key, schema[sweep_key])
        if sweep0_info.id == "readout_amplitude":
            sqil.set_plot_style(plt)
            fig2, ax = plt.subplots(1, 1)
            nrmses = np.ones(len(sweeps[0]))
            last_great, last_idx = None, None
            for i in range(len(sweeps[0])):
                fit_res = sqil.resonator.linmag_fit(x_data[i, :], y_data[i, :])
                nrmses[i] = fit_res.metrics["nrmse"]
                if fit_res.quality(recipe="nrmse") == FitQuality.GREAT:
                    last_great = sweeps[0][i]
                    last_idx = i
            anal_res.extra_data.update({"nrmses": nrmses})
            if last_great is not None:
                anal_res.updated_params["q0"].update({sweep0_info.id: last_great})
                try:
                    anal_res_no_sweep = rr_spec_analysis(
                        datadict=datadict, qpu=qpu, at_idx=last_idx
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
                    anal_res.updated_params["q0"].update(
                        {
                            "readout_resonator_frequency": fit_res.params_by_name["x0"],
                        }
                    )
                    print("Error while analyzing the selected single trace", e)
                finally:
                    # Reset fit res to avoid plotting it
                    fit_res = None

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
            if last_great is not None:
                ax.scatter(
                    last_great,
                    nrmses[last_idx],
                    color="tab:red",
                    zorder=3,
                    s=400,
                    marker="*",
                    label=f"Selected {str(sweep0_info.name).lower()}",
                )
                axs[0].axhline(last_great, color="tab:red", linestyle="--")
            ax.legend()
            fig2.tight_layout()
            anal_res.figures.update({"fig_best_amp": fig2})

    exp_params = get_relevant_exp_parameters(
        qubit_params, ONE_TONE_PARAMS, datadict_map["sweeps"]
    )
    params_str = ",   ".join([qubit_params[id].symbol_and_value for id in exp_params])

    updated_params_info = {
        k: ParamInfo(k, v) for k, v in anal_res.updated_params["q0"].items()
    }
    update_params_str = ",   ".join(
        [updated_params_info[id].symbol_and_value for id in updated_params_info.keys()]
    )

    fig.suptitle("Readout resonator spectroscopy\n" + update_params_str)
    if fit_res:
        fig.text(0.02, -0.02, f"Model: {fit_res.model_name} - {fit_res.quality()}")
    fig.text(0.3, -0.02, "Experiment:   " + params_str, ha="left")
    fig.tight_layout()
    # plt.show()

    return anal_res


# TODO: add power axis
