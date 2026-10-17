import numpy as np
from laboneq.dsl.experiment.pulse_library import register_pulse_functional


@register_pulse_functional
def gaussian_square_sqil(
    x, sigma=1 / 3, padding=10e-9, zero_boundaries=False, *, length, **_
):
    """Create a gaussian square waveform with a square portion of length
    ``length + 2*padding`` and Gaussian shaped sides.

    Arguments:
        length (float):
            Length of the flat part of the pulse in seconds
        padding (float):
            Symmetric padding added on both sides of the pulse to allow
            the gaussian ring up and ring down
        sigma (float):
            Std. deviation of the Gaussian rise/fall portion of the pulse
        zero_boundaries (bool):
            Whether to zero the pulse at the boundaries

    Keyword Arguments:
        uid ([str][]): Unique identifier of the pulse
        amplitude ([float][]): Amplitude of the pulse

    Returns:
        pulse (Pulse): Gaussian square pulse.
    """

    if length < 2 * padding:
        raise ValueError(
            "The total length of the pulse must be >= 2*padding."
            "The default padding is 10e-9."
        )

    width = length - 2 * padding

    risefall_in_samples = round(len(x) * (1 - width / length) / 2)
    flat_in_samples = len(x) - 2 * risefall_in_samples
    gauss_x = np.linspace(-1.0, 1.0, 2 * risefall_in_samples)
    gauss_part = np.exp(-(gauss_x**2) / (2 * sigma**2))
    gauss_sq = np.concatenate(
        (
            gauss_part[:risefall_in_samples],
            np.ones(flat_in_samples),
            gauss_part[risefall_in_samples:],
        )
    )
    if zero_boundaries:
        t_left = gauss_x[0] - (gauss_x[1] - gauss_x[0])
        delta = np.exp(-(t_left**2) / (2 * sigma**2))
        gauss_sq -= delta
        gauss_sq /= 1 - delta
    return gauss_sq


@register_pulse_functional
def sinc(
    x,
    bandwidth=1e6,
    window="hann",
    zero_boundaries=False,
    *,
    length,
    **_,
):
    """
    Create a windowed sinc pulse whose FFT approximates a square spectrum.

    Arguments:
        length (float):
            Total pulse duration (seconds)
        bandwidth (float):
            Target flat spectral bandwidth in Hz
        window (str or None):
            Window applied to truncate the sinc.
            Options: "hann", "gaussian", None
        zero_boundaries (bool):
            Force pulse to zero at boundaries.

    Returns:
        pulse (np.ndarray): Sinc-shaped pulse
    """

    import numpy as np

    # Center time axis
    t = x - np.mean(x)

    # Normalized sinc: np.sinc(z) = sin(pi z)/(pi z)
    pulse = np.sinc(bandwidth * t)

    # ---- Windowing (important physically) ----
    if window == "hann":
        w = np.hanning(len(x))
        pulse *= w

    elif window == "gaussian":
        sigma = length / 6
        w = np.exp(-(t**2) / (2 * sigma**2))
        pulse *= w

    elif window is None:
        pass
    else:
        raise ValueError("window must be 'hann', 'gaussian', or None")

    # ---- Optional boundary normalization ----
    if zero_boundaries:
        pulse -= pulse[0]
        pulse /= np.max(np.abs(pulse))

    # Normalize between -1 and 1
    peak = np.max(np.abs(pulse))
    if peak > 0:
        pulse /= peak  # now in [-1, 1]

    return pulse


@register_pulse_functional
def chirp(
    x,
    f_start,
    f_stop,
    phase=0.0,
    envelope=None,
    complex_output=True,
    zero_boundaries=False,
    normalize=True,
    *,
    length,
    **_,
):
    """
    Linear chirp pulse for SHFQC.

    Arguments:
        length (float):
            Pulse duration (seconds)
        f_start (float):
            Start frequency (Hz)
        f_stop (float):
            Stop frequency (Hz)
        phase (float):
            Initial phase (radians)
        envelope (str or None):
            "hann", "gaussian", or None
        complex_output (bool):
            If True, returns complex IQ chirp.
        zero_boundaries (bool):
            Force pulse edges to zero.
        normalize (bool):
            Normalize waveform to [-1, 1].

    Returns:
        np.ndarray
    """

    import numpy as np

    # ---- Center time axis ----
    z = (x * length + length) / 2
    t = z - np.mean(z)

    T = length
    k = (f_stop - f_start) / T  # chirp rate

    # ---- Phase integral ----
    phi = 2 * np.pi * (f_start * t + 0.5 * k * t**2) + phase

    if complex_output:
        pulse = np.exp(1j * phi)
    else:
        pulse = np.cos(phi)

    # ---- Envelope ----
    if envelope == "hann":
        pulse *= np.hanning(len(x))

    elif envelope == "gaussian":
        sigma = length / 6
        pulse *= np.exp(-(t**2) / (2 * sigma**2))

    elif envelope is None:
        pass
    else:
        raise ValueError("envelope must be 'hann', 'gaussian', or None")

    # ---- Zero boundaries ----
    if zero_boundaries:
        pulse -= pulse[0]

    # ---- SHFQC normalization ----
    peak = np.max(np.abs(pulse))
    if peak > 0:
        pulse /= peak

    return pulse
