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
