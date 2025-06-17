import matplotlib.pyplot as plt
import numpy as np
import scipy  # does this conflict with elementary import above?
from scipy.optimize import curve_fit, fmin

# from laboneq.simple import *


def logsweep(start, stop, npts, base=np.e):
    """
    return a numpy array in log scale
    [start, ....., stop]
    """
    start = np.log(start)
    stop = np.log(stop)
    return np.logspace(start=start, stop=stop, num=npts, endpoint=True, base=base)


def shfqa_power_calculator(ro_power):
    """
    calculate oscillator power range and pulse amplitude
    to get the correct output power for SHFQA out port
    "amp" should must be lower than 0.95 not to overload power range!!

    ro_power = 20 * np.log10(pulse_amp) + power_range
    """
    prange_list = np.linspace(-30, 10, 9)
    # if ro_power > 20*np.log10(0.95) + 10:
    # raise ValueError(f'The maximum power of SHFQC is {20*np.log10(0.95) + 10} dBm!')
    for prange in prange_list:
        # if ro_power <= 20*np.log10(0.95) + prange:
        if ro_power <= prange:
            power_range = prange
            signal_amp = 10 ** ((ro_power - power_range) / 20)
            break
    return power_range, signal_amp


def V_to_dBm(vol):
    power = vol**2 / 50 * 1e3
    dBm = 10 * np.log10(power)
    return dBm


def hdawg_power_calculator(qu_power):
    """
    calculate oscillator power range and pulse amplitude
    to get the correct output power for HDAWG out port
    "amp" should be lower than 0.95 not to overload power range!!

    HDAWG power range is in the unit of [V]
    availabe at 0.2, 0.4, 0.6, 0.8, 1, 2, 3, 4, 5
    correspond to -0.97dBm to 26.9897...(dBm)
    ro_power = 10 * log(pulse_amp**2 * power_range)
    """
    prange_list = [0.2, 0.4, 0.6, 0.8, 1, 2, 3, 4, 5]
    if qu_power > 20 * np.log10(0.95) + V_to_dBm(5):
        raise ValueError(
            f"The maximum power of HDAWG is {20*np.log10(0.95) + V_to_dBm(5)}dBm"
        )
    for prange in prange_list:
        if qu_power <= 20 * np.log10(0.95) + V_to_dBm(prange):
            power_range = prange
            signal_amp = 10 ** ((qu_power - V_to_dBm(power_range)) / 20)
            break
    return power_range, signal_amp


def sparameter_to_dB_phase(array):
    """
    convert array complex s parameters to array of complex(dBm)
    """
    mag = 20 * np.log10(np.abs(array))
    # phase = np.unwrap(np.angle(array),peri)
    phase = np.angle(array)
    return mag, phase


def external_average_loop(session, compiled_exp, external_avg):
    """
    run an compiled exp and take an average
    """
    avg_result = 0
    for _ in range(external_avg):
        laboneq_result = session.run(compiled_exp)
        avg_result += laboneq_result.get_data("exp_measure_handle")
    avg_result /= external_avg
    return avg_result


def external_average_loop_dispersive_ge(session, compiled_exp, external_avg):
    """
    run an compiled exp and take an average
    """
    avg_result0 = 0  # for ground state
    avg_result1 = 0  # for excited state

    for _ in range(external_avg):
        laboneq_result = session.run(compiled_exp)
        avg_result0 += laboneq_result.get_data("ground_state")
        avg_result1 += laboneq_result.get_data("excited_state")
    avg_result0 /= external_avg
    avg_result1 /= external_avg
    return avg_result0, avg_result1


def external_average_loop_dispersive_ef(session, compiled_exp, external_avg):
    """
    run an compiled exp and take an average
    """
    avg_result0 = 0  # for e-state
    avg_result1 = 0  # for f-state

    for _ in range(external_avg):
        laboneq_result = session.run(compiled_exp)
        avg_result0 += laboneq_result.get_data("e_state")
        avg_result1 += laboneq_result.get_data("f_state")
    avg_result0 /= external_avg
    avg_result1 /= external_avg
    return avg_result0, avg_result1


def external_average_loop_interleaved_T1_echo(session, compiled_exp, external_avg):
    """
    run an compiled exp and take an average
    """
    avg_result_T1 = 0  # for T1
    avg_result_echo = 0  # for echo

    for _ in range(external_avg):
        laboneq_result = session.run(compiled_exp)
        avg_result_T1 += laboneq_result.get_data("T1_data")
        avg_result_echo += laboneq_result.get_data("echo_data")
    avg_result_T1 /= external_avg
    avg_result_echo /= external_avg
    return avg_result_T1, avg_result_echo


def external_average_loop_2data(session, compiled_exp, external_avg):
    """
    run an compiled exp and take an average
    """
    avg_result1 = 0  # for handle1
    avg_result2 = 0  # for handle2

    for _ in range(external_avg):
        laboneq_result = session.run(compiled_exp)
        avg_result1 += laboneq_result.get_data("handle1")
        avg_result2 += laboneq_result.get_data("handle2")
    avg_result1 /= external_avg
    avg_result2 /= external_avg
    return avg_result1, avg_result2


def rotate_to_real_axis(complex_values):
    # find angle
    slope, y0 = np.polyfit(np.real(complex_values), np.imag(complex_values), 1)
    angle = np.arctan(slope)

    res_values = (complex_values - 1j * y0) * np.exp(
        -1j * angle
    )  # is it "-"angle?? taketo

    return res_values


def analyze_qspec(
    qspec_res,
    qspec_freq,
    f0=1e9,
    a=0.01,
    gamma=3e6,
    offset=0.04,
    rotate=False,
    flip=False,
):
    """
    Fits data with lorentzian curve for spectroscopy measurement.
    """
    fig = plt.figure()
    ax = fig.add_subplot(111)
    if rotate == True:
        y = np.real(rotate_to_real_axis(qspec_res))
    else:
        y = np.abs(qspec_res)
    ax.plot(qspec_freq, y, marker=".", markersize=1)
    flip_sign = -1 if flip else +1

    def lorentzian(f, f0, a, gamma, offset, flip_sign):
        penalization = abs(min(0, gamma)) * 1000
        return offset + flip_sign * a / (1 + (f - f0) ** 2 / gamma**2) + penalization

    (f_0, a, gamma, offset, flip_sign), _ = curve_fit(
        lorentzian, qspec_freq, y, (f0, a, gamma, offset, flip_sign)
    )

    y_fit = lorentzian(qspec_freq, f_0, a, gamma, offset, flip_sign)

    ax.plot(qspec_freq, y_fit, linewidth=0.8, color="red", label="fit")
    plt.xlabel("RO frequency [Hz]")
    if rotate == True:
        plt.ylabel("Rotated signal a.u.")
    else:
        plt.ylabel("Magnitude [dBm]")
    plt.title("f_0 = " + str(int(f_0)) + "Hz")
    plt.show()
    return f_0, fig


def compute_threshold(result_state0, result_state1, plotting, path):
    """
    For single shot measurement.
    """
    res0 = result_state0
    res1 = result_state1

    # plt.figure()
    # plt.hist(res0.real, bins=100, alpha=0.5,color="blue");
    # plt.hist(res1.real, bins=100, alpha=0.5,color="red");

    # plt.figure()
    # plt.hist(res0.imag, bins=100, alpha=0.5,color="blue");
    # plt.hist(res1.imag, bins=100, alpha=0.5,color="red");

    if plotting == True:
        fig_blob_plot = plt.figure()
        ax_blob_plot = fig_blob_plot.add_subplot(111)
        ax_blob_plot.scatter(res0.real, res0.imag, c="b", alpha=0.1, label="ground")
        ax_blob_plot.scatter(res1.real, res1.imag, c="r", alpha=0.1, label="excited")
        ax_blob_plot.plot(
            np.real(np.mean(res0)),
            np.imag(np.mean(res0)),
            "X",
            markerfacecolor="b",
            markersize=15,
            markeredgewidth=2,
            markeredgecolor="gold",
        )
        ax_blob_plot.plot(
            np.real(np.mean(res1)),
            np.imag(np.mean(res1)),
            "X",
            markerfacecolor="r",
            markersize=15,
            markeredgewidth=2,
            markeredgecolor="gold",
        )
        # ax_blob_plot.plot([threshold, threshold], [min([*res0_rot.imag, *res1_rot.imag, *res0.imag, *res1.imag]), max([*res0_rot.imag, *res1_rot.imag, *res0.imag, *res1.imag]),],"black")
        ax_blob_plot.legend()
        # ax_blob_plot.set_aspect('equal')
        ax_blob_plot.set_title("measured")
        fig_blob_plot.savefig(path + "/blob_plot_measured.png")

    connect_vector = np.mean(res0) - np.mean(res1)  # median instead of mean?
    rotation_angle = -np.angle(connect_vector)
    res0_rot = res0 * np.exp(1j * rotation_angle)
    res1_rot = res1 * np.exp(1j * rotation_angle)
    threshold = (np.median(res0_rot.real) + np.median(res1_rot.real)) / 2

    # plt.figure()
    # plt.hist(res0_rot.real, bins=100, alpha=0.5,color="blue")
    # plt.hist(res1_rot.real, bins=100, alpha=0.5,color="red")

    # plt.figure()
    # plt.hist(res0_rot.imag, bins=100, alpha=0.5,color="blue")
    # plt.hist(res1_rot.imag, bins=100, alpha=0.5,color="red")
    if plotting == True:
        fig_blob_plot_rot = plt.figure()
        ax_blob_plot_rot = fig_blob_plot_rot.add_subplot(111)
        ax_blob_plot_rot.scatter(
            res0_rot.real, res0_rot.imag, c="b", alpha=0.1, label="ground"
        )
        ax_blob_plot_rot.scatter(
            res1_rot.real, res1_rot.imag, c="r", alpha=0.1, label="excited"
        )
        ax_blob_plot_rot.plot(
            np.real(np.mean(res0_rot)),
            np.imag(np.mean(res0_rot)),
            "X",
            markerfacecolor="b",
            markersize=15,
            markeredgewidth=2,
            markeredgecolor="gold",
        )
        ax_blob_plot_rot.plot(
            np.real(np.mean(res1_rot)),
            np.imag(np.mean(res1_rot)),
            "X",
            markerfacecolor="r",
            markersize=15,
            markeredgewidth=2,
            markeredgecolor="gold",
        )
        ax_blob_plot_rot.plot(
            [threshold, threshold],
            [
                min([*res0_rot.imag, *res1_rot.imag, *res0.imag, *res1.imag]),
                max([*res0_rot.imag, *res1_rot.imag, *res0.imag, *res1.imag]),
            ],
            "black",
        )
        ax_blob_plot_rot.legend()
        # ax_blob_plot_rot.set_aspect('equal')
        ax_blob_plot_rot.set_title("rotated")
        fig_blob_plot_rot.savefig(path + "/blob_plot_rotated.png")

    Ie = np.real(res0_rot)
    Ig = np.real(res1_rot)

    bins = 100  # make generic
    fig_projection = plt.figure()
    ax_projection = fig_projection.add_subplot(111)
    ax_projection.set_title("projection of rotated I-quadrature")
    ng, binsg, _ = plt.hist(Ig, bins=bins, density=False, color="b", alpha=0.5)
    ne, binse, _ = plt.hist(Ie, bins=bins, density=False, color="r", alpha=0.5)

    bin_widthg = binsg[1] - binsg[0]
    areag = np.sum(ng) * bin_widthg
    mug, sigmag = scipy.stats.norm.fit(Ig)
    best_fit_lineg = scipy.stats.norm.pdf(
        binsg, np.real(mug), np.real(sigmag)
    ) * np.real(areag)
    ax_projection.plot(binsg, best_fit_lineg, c="b")

    bin_widthe = binse[1] - binse[0]
    areae = np.sum(ne) * bin_widthe
    mue, sigmae = scipy.stats.norm.fit(Ie)
    best_fit_linee = scipy.stats.norm.pdf(
        binse, np.real(mue), np.real(sigmae)
    ) * np.real(areae)
    ax_projection.plot(binse, best_fit_linee, c="r")

    if plotting == False:
        plt.close(fig_projection)
    else:
        fig_projection.savefig(path + "/blob_plot_histogram.png")

    meanVgI = np.mean(Ig)
    meanVeI = np.mean(Ie)
    varVg = np.std(Ig) ** 2
    varVe = np.std(Ie) ** 2

    SNR = np.real(np.abs(meanVgI - meanVeI) / np.sqrt((varVg + varVe)))
    # SNR=np.real(np.abs(meanVgI-meanVeI)**2/(varVg+varVe)) #which definition do we use?

    def fidelity_calc(xg, yg, xe, ye, enable_plot=False):

        x = np.linspace(np.min(xg), np.max(xe), 100)

        fe = scipy.interpolate.interp1d(xe, ye, kind="linear", fill_value="extrapolate")
        fg = scipy.interpolate.interp1d(xg, yg, kind="linear", fill_value="extrapolate")
        ye1 = fe(x)
        ye1[ye1 < 0] = 0
        yg1 = fg(x)
        yg1[yg1 < 0] = 0
        idx = np.min(np.argwhere(yg1 - ye1 < 1e-5))
        if enable_plot:
            plt.figure()
            plt.plot(x, yg1, "-ob", label="|g>")
            plt.plot(x, ye1, "-or", label="|e>")

            plt.plot(x[idx], yg1[idx], "go")

        errorg = scipy.integrate.trapezoid(
            yg1[idx:], x[idx:]
        ) / scipy.integrate.trapezoid(yg1, x)
        errore = scipy.integrate.trapezoid(
            ye1[0:idx], x[0:idx]
        ) / scipy.integrate.trapezoid(ye1, x)

        F = 1 - errore - errorg
        # print('F=',np.real(F)*100)

        return F

    F = fidelity_calc(binsg, best_fit_lineg, binse, best_fit_linee)

    return threshold, SNR, F


def create_pwm_array(pwm_freq, pulse_length, pulse_amp):
    """
    create a piece wise modulated oscillating numpy array for qubit pulses.
    Mainly used for three tone measurement.
    All of the pulse will be enveloped with cos2 function.

    Returns
    -------
        Returns a complex numpy array of the pulse.
        You have to give the array to "pulse_library.sampled_pulse_complex(uid="cos_pwm_pulse", samples=pulse_array)"
        to acquire the LabOneQ pulse object.
    """
    sampling_rate = 2e9

    pulse_env = pulse_library.cos2(
        uid="ge_pi_pulse", length=pulse_length, amplitude=pulse_amp
    )

    timearray, pulse_env = pulse_env.generate_sampled_pulse()
    pulse_env = pulse_env.real  # envelope doesn't have imag
    oscillating_array = np.array(
        [
            np.exp(-1j * 2 * np.pi * pwm_freq * k / sampling_rate)
            for k in range(int(pulse_length * sampling_rate))
        ]
    )

    return pulse_env * oscillating_array


def current_range_check(param_dict):
    """
    Yokogawa current check function
    """
    if np.abs(param_dict["current"]) > param_dict["gs_current_range"]:
        raise ValueError(
            f'current {param_dict["current"]} is out of "gs_current_range" {param_dict["gs_current_range"]}'
        )
