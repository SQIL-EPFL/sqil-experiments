from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import attrs
import numpy as np
from helpers.laboneq import shfqa_power_calculator
from laboneq.core.utilities.dsl_dataclass_decorator import classformatter
from laboneq.dsl.calibration import Calibration, Oscillator, SignalCalibration
from laboneq.dsl.enums import ModulationType
from laboneq.dsl.quantum import QuantumElement, QuantumParameters
from laboneq.simple import dsl

if TYPE_CHECKING:
    from laboneq.dsl.experiment.pulse import Pulse


# TODO: Add support for specifying integration kernels as a list of sample
#       values.


@classformatter
@attrs.define()
class SqilTransmonParameters(QuantumParameters):
    """Qubit parameters for `TunableTransmonQubit` instances.

    Attributes:
        drive_lo_frequency:
            Local oscillator frequency for the drive signals.
        readout_lo_frequency:
            Local oscillator frequency for the readout lines.

        resonance_frequency_ge:
            Resonance frequency of the qubits g-e transition.
        resonance_frequency_ef:
            Resonance frequency of the qubits e-f transition.
        readout_resonator_frequency:
            Readout resonantor frequency of the qubit.

        ge_drive_amplitude_pi:
            Amplitude for a pi pulse on the g-e transition.
        ge_drive_amplitude_pi2:
            Amplitude for a half-pi pulse on the g-e transition.
        ge_drive_length:
            Length of g-e transition drive pulses (seconds).
        ge_drive_pulse:
            Pulse parameters for g-e transition drive pulses.

        ef_drive_amplitude_pi:
            Amplitude for a pi pulse on the e-f transition.
        ef_drive_amplitude_pi2:
            Amplitude for a half-pi pulse on the e-f transition.
        ef_drive_length:
            Length of e-f transition drive pulses (seconds).
        ef_drive_pulse:
            Pulse parameters for e-f transition drive pulses.

        qubit_resonator_coupling_strength_g:
            Qubit resonator coupling strength.
        ge_chi_shift:
            Chi shift of the ground state and first excited state.

        readout_amplitude:
            Readout pulse amplitude.
        readout_length:
            Readout pulse length.
        readout_pulse:
            Pulse parameters for the readout pulse.
        readout_integration_length:
            Duration of the weighted integration.
        readout_integration_delay:
            Integration delay between readout pulse and data acquisition.
            Defaults to 20 ns.
        readout_integration_kernels_type:
            The type of integration kernel to use, either "default" or "optimal".
            Setting this parameter to "optimal" disables the modulation in the acquire
            signal, as the optimal kernels are assumed to be already modulated.
        readout_integration_kernels:
            Either "default" or a list of pulse dictionaries.
        readout_integration_discrimination_thresholds:
            Either `None` or a list of thresholds.

        reset_delay_length:
            Duration of the wait time for reset.

        drive_range:
            Drive power setting, defaults to 10 dBm.
        readout_range_out:
            Readout output power setting, defaults to 5 dBm.
        readout_range_in:
            Readout input power setting, defaults to 10 dBm.

        spectroscopy_length:
            Length of the qubit drive pulse in spectroscopy (seconds).
        spectroscopy_amplitude:
            Amplitude of the qubit drive pulse in spectroscopy.

        dc_slot:
            Slot number on the DC source used for applying a DC voltage to the qubit.
        dc_voltage_parking:
            Qubit DC parking voltage.
        flux_offset_voltage:
            Offset voltage for flux control line - defaults to 0.
    """

    # Helper parameter used to repeat experiments
    index: int = 0

    # qubit coherence times

    ge_T1: float = 0  # noqa: N815
    ge_T2: float = 0  # noqa: N815
    ge_T2_star: float = 0  # noqa: N815
    ef_T1: float = 0  # noqa: N815
    ef_T2: float = 0  # noqa: N815
    ef_T2_star: float = 0  # noqa: N815

    # local oscillators

    drive_lo_frequency: float | None = None
    readout_lo_frequency: float | None = None
    readout_external_lo_frequency: float | None = None
    readout_external_lo_power: float | None = None

    # resonance frequencies

    resonance_frequency_ge: float | None = None
    resonance_frequency_ef: float | None = None
    readout_resonator_frequency: float | None = None

    # readout resonator parameters
    readout_configuration: Literal["reflection", "hanger", "transmission"] | None = None
    readout_kappa_tot: float | None = None

    # g-e drive pulse parameters

    ge_drive_amplitude_pi: float = 0.2
    ge_drive_amplitude_pi2: float = 0.1
    ge_drive_length: float = 50e-9
    ge_drive_pulse: dict = attrs.field(
        factory=lambda: {"function": "gaussian_square", "can_compress": True},
    )

    # e-f drive pulse parameters

    ef_drive_amplitude_pi: float = 0.2
    ef_drive_amplitude_pi2: float = 0.1
    ef_drive_length: float = 50e-9
    ef_drive_pulse: dict = attrs.field(
        factory=lambda: {
            "function": "drag",
            "beta": 0,
            "sigma": 0.25,
        },
    )

    # qubit-resonator coupling parameters

    qubit_resonator_coupling_strength_g: float = 0
    ge_chi_shift: float = 0

    # readout and integration parameters

    readout_amplitude: float = 1.0
    readout_length: float = 2e-6
    readout_pulse: dict = attrs.field(
        factory=lambda: {
            "function": "const",
        },
    )
    readout_integration_length: float = 2e-6
    readout_integration_delay: float = 20e-9
    readout_integration_kernels_type: Literal["default", "optimal"] = "default"
    readout_integration_kernels: list[dict] | None = None
    readout_integration_discrimination_thresholds: list[float] | None = None

    # reset parameters

    reset_delay_length: float | None = 200e-6

    # power range parameters

    drive_range: float = 10
    readout_range_out: float = 10
    readout_range_in: float = -20
    ro_power: float = -30

    # spectroscopy parameters

    spectroscopy_length: float | None = 5e-6
    spectroscopy_amplitude: float | None = 1
    spectroscopy_pulse: dict = attrs.field(
        factory=lambda: {
            "function": "const",
            "can_compress": True,
        },
    )

    # flux parameters

    dc_slot: int | None = 0
    dc_voltage_parking: float | None = 0.0
    flux_offset_voltage: float = 0.0

    def replace(self, **changes: dict[str, object]):
        """Return a new set of parameters with changes applied.

        Arguments:
            changes:
                Parameter changes to apply passed as keyword arguments.
                Dotted key names such as `a.b.c` update nested parameters
                or items within parameter values that are dictionaries.

        Return:
            A new parameters instance.
        """
        invalid_params = self._get_invalid_param_paths(**changes)
        if invalid_params:
            raise ValueError(
                f"Update parameters do not match the qubit "
                f"parameters: {invalid_params}",
            )

        # Automatically update range and amplitude when "power" parameters are changed
        # TODO: handle all power variables
        keys = changes.keys()
        if "ro_power" in keys:
            range, amp = shfqa_power_calculator(changes["ro_power"])
            changes = {**changes, "readout_range_out": range, "readout_amplitude": amp}

        return self._nested_evolve(self, **changes)

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
        ext_lo = self.readout_external_lo_frequency or 0
        return self.readout_resonator_frequency - self.readout_lo_frequency - ext_lo

    @property
    def readout_power(self) -> float | None:
        ext_power = self.readout_external_lo_power or 0
        return 20 * np.log10(self.readout_amplitude) + self.readout_range_in + ext_power

    @property
    def ge_drive_power_pi(self):
        return 20 * np.log10(self.ge_drive_amplitude_pi) + self.drive_range


@classformatter
@attrs.define()
class SqilTransmon(QuantumElement):
    """A class for a superconducting, flux-tuneable Transmon Qubit."""

    PARAMETERS_TYPE = SqilTransmonParameters
    REQUIRED_SIGNALS = (
        "acquire",
        "drive",
        "measure",
    )
    OPTIONAL_SIGNALS = (
        "drive_ef",
        "flux",
    )

    TRANSITIONS = ("ge", "ef")

    def transition_parameters(self, transition: str | None = None) -> tuple[str, dict]:
        """Return the transition drive signal line and parameters.

        Arguments:
            transition:
                The transition to return parameters for. May be `None`,
                `"ge"` or `"ef"`. `None` defaults to `"ge"`.

        Returns:
            line:
                The drive line for the transition.
            params:
                The drive parameters for the transition.

        Raises:
            ValueError:
                If the transition is not `None`, `"ge"` or `"ef"`.
        """
        if transition is None:
            transition = "ge"
        if transition not in self.TRANSITIONS:
            raise ValueError(
                f"Transition {transition!r} is not one of None, 'ge' or 'ef'.",
            )
        line = "drive" if transition == "ge" else "drive_ef"

        param_keys = ["amplitude_pi", "amplitude_pi2", "length", "pulse"]
        params = {
            k: getattr(self.parameters, f"{transition}_drive_{k}") for k in param_keys
        }

        return line, params

    def readout_parameters(self) -> tuple[str, dict]:
        """Return the measure line and the readout parameters.

        Returns:
           line:
               The measure line of the qubit.
           params:
               The readout parameters.
        """
        param_keys = ["amplitude", "length", "pulse"]
        params = {k: getattr(self.parameters, f"readout_{k}") for k in param_keys}
        return "measure", params

    def readout_integration_parameters(self) -> tuple[str, dict]:
        """Return the acquire line and the readout integration parameters.

        Returns:
           line:
               The acquire line of the qubit.
           params:
               The readout integration parameters.
        """
        param_keys = ["length", "kernels", "kernels_type", "discrimination_thresholds"]
        params = {
            k: getattr(self.parameters, f"readout_integration_{k}") for k in param_keys
        }
        return "acquire", params

    def spectroscopy_parameters(self) -> tuple[str, dict]:
        """Return the qubit-spectroscopy line and the spectroscopy-pulse parameters.

        Returns:
           line:
               The qubit-spectroscopy drive line of the qubit.
           params:
               The spectroscopy-pulse parameters.
        """
        param_keys = ["amplitude", "length", "pulse"]
        params = {k: getattr(self.parameters, f"spectroscopy_{k}") for k in param_keys}
        return "drive", params

    def default_integration_kernels(self) -> list[Pulse]:
        """Return a default list of integration kernels.

        Returns:
            A list consisting of a single constant pulse with length equal to
            `readout_integration_length`.
        """
        return [
            dsl.create_pulse(
                {
                    "function": "const",
                    "length": self.parameters.readout_integration_length,
                    "amplitude": 1.0,
                },
                name=f"integration_kernel_{self.uid}",
            ),
        ]

    def get_integration_kernels(
        self,
        kernel_pulses: list[dict] | str | None = None,
    ) -> list[Pulse]:
        """Create readout integration kernels for the transmon.

        Arguments:
            kernel_pulses:
                Custom definitions for the kernel pulses, passed as a list of
                pulse dictionaries, or the values "default" or "optimal".

        If `kernel_pulses` are passed as a list of pulse dictionaries, they are
        returned as pulse functionals.

        The special value `"optimal"` for `kernel_pulses` or for
        `readout_integration_kernels_type` if kernel_pulses is None, returns
        `TunableTransmonParameters.readout_integration_kernels`.

        The special value `"default"` for either `kernel_pulses` or
        `readout_integration_kernels_type` parameter returns
        the default kernels from `.default_integration_kernels()`.


        Returns:
            A list of integration kernel pulses.
        """
        if kernel_pulses is None:
            kernel_pulses = self.parameters.readout_integration_kernels_type

        if kernel_pulses == "default":
            integration_kernels = self.default_integration_kernels()
        elif kernel_pulses == "optimal":
            kernel_params = self.parameters.readout_integration_kernels
            if isinstance(kernel_params, (list, tuple)) and len(kernel_params) > 0:
                integration_kernels = [
                    dsl.create_pulse(
                        kernel_pulse, name=f"integration_kernel_{self.uid}"
                    )
                    for kernel_pulse in kernel_params
                ]
            else:
                raise TypeError(
                    f"{self.__class__.__name__}.parameters.readout_integration_kernels'"
                    f" should be a list of pulse dictionaries."
                )
        elif isinstance(kernel_pulses, (list, tuple)) and kernel_pulses:
            integration_kernels = [
                dsl.create_pulse(kernel_pulse, name=f"integration_kernel_{self.uid}")
                for kernel_pulse in kernel_pulses
            ]
        else:
            raise TypeError(
                f"The readout integration kernels should be a list of pulse "
                f"dictionaries or the values 'default' or 'optimal'. If no readout "
                f"integration kernels have been specified, then the parameter "
                f"{self.__class__.__name__}.parameters.readout_integration_kernels_type'"
                f" should be either 'default' or 'optimal'."
            )

        return integration_kernels

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
