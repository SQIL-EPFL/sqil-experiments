from laboneq.dsl.parameter import SweepParameter
from laboneq.simple import dsl

from sqil_experiments.qpu.sqil_transmon.operations import SqilTransmonOperations
from sqil_experiments.qpu.sqil_transmon.qubit import SqilTransmon

# gap between two tones on the same channel (time for the oscillator switch)
AUX_GAP = 100e-9


class ResetOperations(SqilTransmonOperations):
    """SqilTransmonOperations with the reset tone (aux line) in passive_reset."""

    def __init__(self, aux_order: list[str] | None = None):
        """
        aux_order:
            Qubits whose reset tones share the SG channel, in the order in
            which the tones are played (one after the other). The tone of
            the n-th qubit starts n * (aux_drive_length + 100 ns) after the
            readout, so all tones must have the same aux_drive_length.
            None: the tone starts right after the readout (one qubit).
        """
        super().__init__()
        self.aux_order = list(aux_order or [])

    @dsl.quantum_operation
    def passive_reset(
        self,
        q: SqilTransmon,
        delay: float | SweepParameter | None = None,
        aux=False,
    ) -> None:
        """Reset tone on the aux line (if aux_drive_amplitude_pi > 0), then wait.

        Arguments:
            q:
                The qubit to reset.
            delay:
                The duration of the wait in seconds. Defaults
                to the qubit parameter `reset_delay_length`.
        """
        if delay is None:
            delay = (
                q.parameters.reset_delay_length
                if not aux
                else q.parameters.aux_reset_delay_length
            )
        if not aux and "aux" in q.signals and q.parameters.aux_drive_amplitude_pi:
            # wait for the tones of the qubits before this one (one tone at a time)
            slot = self.aux_order.index(q.uid) if q.uid in self.aux_order else 0
            if slot:
                self.delay(q, time=slot * (q.parameters.aux_drive_length + AUX_GAP))
            # reset tone, then the wait (both as sections, like Andrea's `reset`)
            self.aux_drive(q)
            self.delay(q, time=delay)
        else:
            # no reset tone: exactly Andrea's passive_reset
            self.delay.omit_section(q, time=delay)
