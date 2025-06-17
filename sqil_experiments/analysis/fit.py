import sqil_core as sqil


def fit_lorentzian_or_gaussian(x_data, y_data, tol=0.1):
    # Try to find the peak
    # x0, fwhm, peak_height, y0, is_peak = sqil.fit.estimate_peak(x_data, y_data)
    # If the peak is not tall enough return
    # if np.abs(peak_height / np.median(y_data)) < tol:
    #     return None

    fit_lor = sqil.fit.fit_lorentzian(x_data, y_data)
    fit_gauss = sqil.fit.fit_gaussian(x_data, y_data)

    # Find the best model
    delta_aic = fit_lor.metrics["aic"] - fit_gauss.metrics["aic"]
    if delta_aic >= 0:
        print(f"Gaussian fit is better   ΔAIC = {delta_aic:.4f}")
        return fit_gauss
    print(f"Lorentzian fit is better ΔAIC = {delta_aic:.4f}")
    return fit_lor


def find_peaked_resonance(freq, mag, phase):
    fit_res = None
    fit_mag = fit_lorentzian_or_gaussian(freq, mag)
    fit_phase = fit_lorentzian_or_gaussian(freq, phase)

    nrmse_mag = fit_mag.metrics["nrmse"]
    nrmse_phase = fit_phase.metrics["nrmse"]

    # If both single fits have acceptable error
    if nrmse_mag < 0.1 and nrmse_phase < 0.1:
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
            lorentzian_dominates = (
                is_mag_lorentzian
                if nrmse_mag - nrmse_phase < 0
                else is_phase_lorentzian
            )
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
        if fit_res.metrics["nrmse"] > 0.1:
            fit_res = fit_mag if nrmse_mag < nrmse_phase else fit_phase

    # In case only one fit has acceptable error, return that
    elif nrmse_mag < 0.1:
        fit_res = fit_mag
    elif nrmse_phase < 0.1:
        fit_res = fit_phase

    return fit_res
