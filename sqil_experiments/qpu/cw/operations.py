from __future__ import annotations

from typing import TYPE_CHECKING, cast

import numpy as np
from laboneq.dsl.calibration import Calibration, Oscillator
from laboneq.dsl.enums import ModulationType
from laboneq.dsl.parameter import SweepParameter
from laboneq.simple import dsl
from sqil_core.experiment.instruments.vna import VNA

from sqil_experiments.qpu.cw.qubit import CwQubit

if TYPE_CHECKING:
    from collections.abc import Sequence

    from laboneq_applications.typing import QuantumElements


class CwQubitOperations(dsl.QuantumOperations):
    """Operations for CwQubit."""

    QUBIT_TYPES = CwQubit

    # TODO: Delete
    @dsl.quantum_operation
    def set_frequency(
        self,
        q: CwQubit,
        frequency: float | SweepParameter,
        *,
        transition: str | None = None,
        readout: bool = False,
        rf: bool = True,
        calibration: Calibration | None = None,
    ) -> None:
        """Sets the frequency of the given qubit drive line or readout line.

        Arguments:
            q:
                The qubit to set the transition or readout frequency of.
            frequency:
                The frequency to set in Hz.
                By default the frequency specified is the RF frequency.
                The oscillator frequency may be set directly instead
                by passing `rf=False`.
            transition:
                The transition to rotate. By default this is "ge"
                (i.e. the 0-1 transition).
            readout:
                If true, the frequency of the readout line is set
                instead. Setting the readout frequency to a sweep parameter
                is only supported in spectroscopy mode. The LabOne Q compiler
                will raise an error in other modes.
            rf:
                If True, set the RF frequency of the transition.
                If False, set the oscillator frequency directly instead.
                The default is to set the RF frequency.
            calibration:
                The experiment calibration to update (see the note below).
                By default, the calibration from the currently active
                experiment context is used. If no experiment context is
                active, for example when using
                `@qubit_experiment(context=False)`, the calibration
                object may be passed explicitly.

        Raises:
            RuntimeError:
                If there is an attempt to call `set_frequency` more than
                once on the same signal. See notes below for details.

        Notes:
            Currently `set_frequency` is implemented by setting the
            appropriate oscillator frequencies in the experiment calibration.
            This has two important consequences:

            * Each experiment may only set one frequency per signal line,
              although this may be a parameter sweep.

            * The set frequency or sweep applies for the whole experiment
              regardless of where in the experiment the frequency is set.

            This will be improved in a future release.
        """
        if readout:
            signal_line, _ = q.readout_parameters()
            lo_frequency = q.parameters.readout_lo_frequency
            external_lo_frequency = q.parameters.readout_external_lo_frequency or 0
        else:
            signal_line, _ = q.transition_parameters(transition)
            lo_frequency = q.parameters.drive_lo_frequency
            external_lo_frequency = 0

        if rf:
            # This subtraction works for both numbers and SweepParameters
            frequency -= lo_frequency + external_lo_frequency

        if calibration is None:
            calibration = dsl.experiment_calibration()
        signal_calibration = calibration[q.signals[signal_line]]
        oscillator = signal_calibration.oscillator

        if oscillator is None:
            oscillator = signal_calibration.oscillator = Oscillator(frequency=frequency)
        if getattr(oscillator, "_set_frequency", False):
            # We mark the oscillator with a _set_frequency attribute to ensure that
            # set_frequency isn't performed on the same oscillator twice. Ideally
            # LabOne Q would provide a set_frequency DSL method that removes the
            # need for setting the frequency on the experiment calibration.
            raise RuntimeError(
                f"Frequency of qubit {q.uid} {signal_line} line was set multiple times"
                f" using the set_frequency operation.",
            )

        oscillator._set_frequency = True
        oscillator.frequency = frequency
        if readout:
            # LabOne Q does not support software modulation of measurement
            # signal sweeps because it results in multiple readout waveforms
            # on the same readout signal. Ideally the LabOne Q compiler would
            # sort this out for us when the modulation type is AUTO, but currently
            # it does not.
            oscillator.modulation_type = ModulationType.HARDWARE

    #
    @dsl.quantum_operation
    def set_readout_amplitude(
        self,
        q: CwQubit,
        amplitude: float | SweepParameter,
        *,
        calibration: Calibration | None = None,
    ) -> None:
        """Sets the readout amplitude of the given qubit's measure line.

        Arguments:
            q:
                The qubit to set the readout amplitude of.
            amplitude:
                The amplitude to set for the measure line
                in units from 0 (no power) to 1 (full scale).
            calibration:
                The experiment calibration to update (see the note below).
                By default, the calibration from the currently active
                experiment context is used. If no experiment context is
                active, for example when using
                `@qubit_experiment(context=False)`, the calibration
                object may be passed explicitly.

        Raises:
            RuntimeError:
                If there is an attempt to call `set_readout_amplitude` more than
                once on the same signal. See notes below for details.

        Notes:
            Currently `set_readout_amplitude` is implemented by setting the
            amplitude of the measure line signal in the experiment calibration.
            This has two important consequences:

            * Each experiment may only set one amplitude per readout line,
                although this may be a parameter sweep.

            * The set readout amplitude or sweep applies for the whole experiment
                regardless of where in the experiment the amplitude is set.

            This will be improved in a future release.
        """
        if calibration is None:
            calibration = dsl.experiment_calibration()
        measure_line, _ = q.readout_parameters()
        signal_calibration = calibration[q.signals[measure_line]]

        if getattr(calibration, "_set_readout_amplitude", False):
            # We mark the oscillator with a _set_readout_amplitude attribute to ensure
            # that set_readout_amplitude isn't performed on the same signal twice.
            # Ideally LabOne Q DSL provide a more direct method that removes the
            # need for setting amplitude on the experiment calibration.
            raise RuntimeError(
                f"Readout amplitude of qubit {q.uid}"
                f" measure line was set multiple times"
                f" using the set_readout_amplitude operation.",
            )

        calibration._set_readout_amplitude = True
        signal_calibration.amplitude = amplitude

    @dsl.quantum_operation
    def measure(
        self, q: CwQubit, handle: str, freq_range: tuple[float, float, int] = None
    ) -> None:
        """Perform a measurement on the qubit at fixed frequency."""
        measure_line, ro_params = q.readout_parameters()
        power = ro_params["power"]

        if freq_range is None:
            f0 = q.parameters.readout_resonator_frequency
            freq_range = (f0, f0, 1)

        measure_line = cast(VNA, measure_line)
        measure_line.set_power(power)
        measure_line.set_frequency_range(*freq_range)

    @dsl.quantum_operation
    def measure_ro_frequency_sweep(
        self,
        q: CwQubit,
        handle: str,
    ) -> None:
        """Perform a measurement on the qubit while sweeping readout frequency."""
        measure_line, ro_params = q.readout_parameters()
        acquire_line, ro_acquire_params = q.readout_integration_parameters()

        power = ro_params["power"]
        start, stop, n_points = ro_params["frequency_sweep"]

        measure_line = cast(VNA, measure_line)
        measure_line.set_power(power)
        measure_line.set_frequency_range(start, stop, n_points)

    @dsl.quantum_operation
    def acquire(
        self,
        q: CwQubit,
        handle: str,
    ) -> None:
        """Perform an acquisition on the qubit."""
        acquire_line, ro_acquire_params = q.readout_integration_parameters()

        bandwidth = ro_acquire_params["bandwidth"]
        averages = ro_acquire_params["averages"]

        acquire_line = cast(VNA, acquire_line)
        acquire_line.set_bandwidth(bandwidth)
        acquire_line.set_averages(averages)
        return acquire_line.get_IQ_data()
