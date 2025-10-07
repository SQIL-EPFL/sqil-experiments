from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import attrs
from laboneq.core.utilities.dsl_dataclass_decorator import classformatter
from laboneq.dsl.calibration import Calibration, Oscillator, SignalCalibration
from laboneq.dsl.enums import ModulationType
from laboneq.dsl.quantum import QuantumElement, QuantumParameters


@classformatter
@attrs.define()
class CwQubitParameters(QuantumParameters):
    # resonance frequencies
    resonance_frequency_ge: float | None = None
    resonance_frequency_ef: float | None = None
    readout_resonator_frequency: float | None = None

    # qubit-resonator coupling parameters
    ge_chi: float = 0

    # readout resonator parameters
    readout_power: float = -40
    readout_configuration: Literal["reflection", "hanger", "transmission"] | None = None
    readout_kappa_tot: float | None = None

    # readout acquisition parameters
    readout_acquire_bandwith: float = 1e3
    readout_acquire_averages: float = 1

    # drive parameters
    drive_frequency: float = 5e9
    drive_power: float = -40

    # current parameters
    current: float | None = None
    current_half_flux: float | None = None
    current_zero_flux: float | None = None

    # local oscillators
    drive_lo_frequency: float | None = None
    drive_lo_power: float | None = None
    readout_lo_frequency: float | None = None
    readout_lo_power: float | None = None

    # Helper parameter used to repeat experiments
    index: int = 0

    @property
    def drive_frequency_ge(self) -> float | None:
        """Qubit drive frequency for the g-e transition."""
        if self.drive_lo_frequency is None or self.resonance_frequency_ge is None:
            return None
        return self.resonance_frequency_ge - self.drive_lo_frequency

    @property
    def drive_frequency_ef(self) -> float | None:
        """Qubit drive frequency for the e-f transition."""
        if self.drive_lo_frequency is None or self.resonance_frequency_ef is None:
            return None
        return self.resonance_frequency_ef - self.drive_lo_frequency

    @property
    def readout_frequency(self) -> float | None:
        """Readout baseband frequency."""
        if (
            self.readout_lo_frequency is None
            or self.readout_resonator_frequency is None
        ):
            return None
        return self.readout_resonator_frequency - self.readout_lo_frequency


@classformatter
@attrs.define()
class CwQubit(QuantumElement):
    """A qubit measured in continuous wave (CW)."""

    PARAMETERS_TYPE = CwQubitParameters
    # Could be turned pointers to instruments to use in operations or
    # in a processing engine
    REQUIRED_SIGNALS = (
        # "acquire",
        # "drive",
        # "measure",
    )
    OPTIONAL_SIGNALS = (
        # "drive_ef",
        # "flux",
    )

    TRANSITIONS = ("ge", "ef")

    def transition_parameters(self) -> tuple[str, dict]:
        """Return the transition drive signal line and parameters.

        Returns:
            line:
               The drive line of the qubit.
            params:
                The drive parameters for the transition.
        """
        param_keys = ["power"]
        params = {k: getattr(self.parameters, f"drive_{k}") for k in param_keys}

        return "drive", params

    def readout_parameters(self) -> tuple[str, dict]:
        """Return the measure line and the readout parameters.

        Returns:
           line:
               The measure line of the qubit.
           params:
               The readout parameters.
        """
        param_keys = ["power"]
        params = {k: getattr(self.parameters, f"readout_{k}") for k in param_keys}
        return "measure", params

    def readout_acquire_parameters(self) -> tuple[str, dict]:
        """Return the acquire line and the readout acquire parameters.

        Returns:
           line:
               The acquire line of the qubit.
           params:
               The readout acquire parameters.
        """
        param_keys = ["bandwidth", "averages"]
        params = {
            k: getattr(self.parameters, f"readout_acquire_{k}") for k in param_keys
        }
        return "acquire", params

    # TODO: delete?
    def calibration(self) -> Calibration:  # noqa: C901, PLR0912
        """Generate calibration from the parameters and attached signal lines.

        Set the readout_integration_discrimination_thresholds and disable the modulation
        of the acquire oscillator if optimal weights are used
        (readout_integration_kernels_type == "optimal")

        Returns:
            calibration:
                Prefilled calibration object from Qubit parameters.
        """
        drive_lo = None
        readout_lo = None

        if self.parameters.drive_lo_frequency is not None:
            drive_lo = Oscillator(
                uid=f"{self.uid}_drive_local_osc",
                frequency=self.parameters.drive_lo_frequency,
            )
        if self.parameters.readout_lo_frequency is not None:
            readout_lo = Oscillator(
                uid=f"{self.uid}_readout_local_osc",
                frequency=self.parameters.readout_lo_frequency,
            )
        if self.parameters.readout_frequency is not None:
            readout_oscillator = Oscillator(
                uid=f"{self.uid}_readout_acquire_osc",
                frequency=self.parameters.readout_frequency,
                modulation_type=ModulationType.AUTO,
            )

        calibration_items = {}
        if "drive" in self.signals:
            sig_cal = SignalCalibration()
            if self.parameters.drive_frequency_ge is not None:
                sig_cal.oscillator = Oscillator(
                    uid=f"{self.uid}_drive_ge_osc",
                    frequency=self.parameters.drive_frequency_ge,
                    modulation_type=ModulationType.AUTO,
                )
            sig_cal.local_oscillator = drive_lo
            sig_cal.range = self.parameters.drive_range
            calibration_items[self.signals["drive"]] = sig_cal
        if "drive_ef" in self.signals:
            sig_cal = SignalCalibration()
            if self.parameters.drive_frequency_ef is not None:
                sig_cal.oscillator = Oscillator(
                    uid=f"{self.uid}_drive_ef_osc",
                    frequency=self.parameters.drive_frequency_ef,
                    modulation_type=ModulationType.AUTO,
                )
            sig_cal.local_oscillator = drive_lo
            sig_cal.range = self.parameters.drive_range
            calibration_items[self.signals["drive_ef"]] = sig_cal
        if "measure" in self.signals:
            sig_cal = SignalCalibration()
            if self.parameters.readout_frequency is not None:
                sig_cal.oscillator = readout_oscillator
            sig_cal.local_oscillator = readout_lo
            sig_cal.range = self.parameters.readout_range_out
            calibration_items[self.signals["measure"]] = sig_cal
        if "acquire" in self.signals:
            sig_cal = SignalCalibration()
            if self.parameters.readout_frequency is not None:
                sig_cal.oscillator = readout_oscillator
            sig_cal.local_oscillator = readout_lo
            sig_cal.range = self.parameters.readout_range_in
            sig_cal.port_delay = self.parameters.readout_integration_delay
            sig_cal.threshold = (
                self.parameters.readout_integration_discrimination_thresholds
            )
            if self.parameters.readout_integration_kernels_type == "optimal":
                sig_cal.oscillator = Oscillator(
                    frequency=0, modulation_type=ModulationType.SOFTWARE
                )
            calibration_items[self.signals["acquire"]] = sig_cal
        if "flux" in self.signals:
            calibration_items[self.signals["flux"]] = SignalCalibration(
                voltage_offset=self.parameters.flux_offset_voltage,
            )
        return Calibration(calibration_items)
