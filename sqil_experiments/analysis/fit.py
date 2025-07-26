from typing import Literal

import sqil_core as sqil
from sqil_core.fit import FitQuality, FitResult


def fit_lorentzian_or_gaussian(x_data, y_data) -> FitResult:
    fit_lor = sqil.fit.fit_lorentzian(x_data, y_data)
    fit_gauss = sqil.fit.fit_gaussian(x_data, y_data)
    return sqil.fit.get_best_fit(fit_lor, fit_gauss, recipe="nrmse_aic")


def find_shared_peak(freq, mag, phase, full_output=False) -> FitResult:
    fit_res = None
    selected_fit_trace: Literal["both", "mag", "phase"] | None = "both"

    fit_mag = fit_lorentzian_or_gaussian(freq, mag)
    fit_phase = fit_lorentzian_or_gaussian(freq, phase)

    nrmse_mag = fit_mag.metrics["nrmse"]
    nrmse_phase = fit_phase.metrics["nrmse"]

    # If both single fits have acceptable error
    if fit_mag.is_acceptable("nrmse") and fit_phase.is_acceptable("nrmse"):
        is_mag_lorentzian = fit_mag.model_name == "lorentzian"
        is_phase_lorentzian = fit_phase.model_name == "lorentzian"
        # If both fit best as loretzians, fit a lorentzian with a shared x0
        if is_mag_lorentzian and is_phase_lorentzian:
            fit_res = sqil.fit.fit_two_lorentzians_shared_x0(freq, mag, freq, phase)
        # If both fit best as gaussians, fit a gaussian with a shared x0
        elif (not is_mag_lorentzian) and (not is_phase_lorentzian):
            fit_res = sqil.fit.fit_two_gaussians_shared_x0(freq, mag, freq, phase)
        # Otherwise, fit both using the model that fits best one of them
        else:
            # Check if the lorentzian or gaussian model dominate on one side
            if nrmse_mag - nrmse_phase < 0:
                lorentzian_dominates = is_mag_lorentzian
            else:
                lorentzian_dominates = is_phase_lorentzian
            print(
                "Lorentzian domninates"
                if lorentzian_dominates
                else "Gaussian dominates"
            )
            print(f" -> nrmse: {nrmse_mag:.4f} vs {nrmse_phase:.4f}")
            # Choose the right model
            if lorentzian_dominates:
                fit_res = fit_res = sqil.fit.fit_two_lorentzians_shared_x0(
                    freq, mag, freq, phase
                )
            else:
                fit_res = sqil.fit.fit_two_gaussians_shared_x0(freq, mag, freq, phase)

        # Check the nrmse of the shared fit. If bad return the best single fit
        if not fit_res.is_acceptable("nrmse"):
            fit_res = fit_mag if nrmse_mag < nrmse_phase else fit_phase

    # In case only one fit has acceptable error, return that
    elif fit_mag.is_acceptable("nrmse"):
        fit_res = fit_mag
        selected_fit_trace = "mag"
    elif fit_phase.is_acceptable("nrmse"):
        fit_res = fit_phase
        selected_fit_trace = "phase"
    else:
        fit_res = None
        selected_fit_trace = None

    return fit_res if not full_output else (fit_res, selected_fit_trace)
