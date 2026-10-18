import numpy as np
from laboneq.dsl.experiment import pulse_library


def sample_unit_amplitude(
    pulse_params: dict,
    length: float,
    sampling_interval: float,
) -> np.ndarray:
    """Generate a unit-amplitude waveform from a registered pulse functional."""

    params = dict(pulse_params)
    function_name = params.pop("function")

    for key in ("length", "amplitude", "sampling_rate", "uid", "name"):
        params.pop(key, None)

    n_samples = int(round(length / sampling_interval))

    if n_samples < 1:
        raise ValueError("Pulse length must span at least one sample.")

    # Check that the duration aligns with the sampling grid.
    actual_length = n_samples * sampling_interval
    if not np.isclose(actual_length, length, rtol=0, atol=1e-15):
        raise ValueError(
            f"Pulse length {length} s is not aligned with the "
            f"sampling interval {sampling_interval} s."
        )

    x = np.linspace(-1.0, 1.0, n_samples)

    sampler = pulse_library.pulse_sampler(function_name)

    samples = np.asarray(
        sampler(
            x,
            length=length,
            amplitude=1.0,
            sampling_rate=1.0 / sampling_interval,
            **params,
        )
    )

    if samples.shape != x.shape:
        raise ValueError(f"{function_name!r} returned an unexpected waveform shape.")

    return samples


def concatenate_pulses(
    pulse_a: dict,
    length_a: float,
    amplitude_a: float,
    pulse_b: dict,
    length_b: float,
    amplitude_b: float,
    gap: float = 0.0,
    name: str = "concatenated",
    sampling_interval: float = 1e-9,
    can_compress=False,
):
    """Create a sampled readout + reset pulse.

    sampling_interval is the time between waveform samples, in seconds.
    """

    if not np.isfinite(sampling_interval) or sampling_interval <= 0:
        raise ValueError("Sampling interval must be positive and finite.")

    if gap < 0:
        raise ValueError("The gap must be non-negative.")

    ro_unit = sample_unit_amplitude(pulse_a, length_a, sampling_interval)

    reset_unit = sample_unit_amplitude(pulse_b, length_b, sampling_interval)

    # Convert a time duration to a number of samples.
    n_gap = int(round(gap / sampling_interval))

    # Avoid silently changing a gap that does not fit the sample grid.
    if not np.isclose(n_gap * sampling_interval, gap, rtol=0, atol=1e-15):
        raise ValueError("Gap is not aligned with the sampling interval.")

    dtype = np.result_type(ro_unit, reset_unit, amplitude_a, amplitude_b)

    samples = np.concatenate(
        [
            amplitude_a * ro_unit,
            np.zeros(n_gap, dtype=dtype),
            amplitude_b * reset_unit,
        ]
    )

    # Number of samples multiplied by seconds per sample.
    combined_length = len(samples) * sampling_interval

    pulse = pulse_library.sampled_pulse(
        samples=samples, uid=name, can_compress=can_compress
    )

    return pulse, combined_length
