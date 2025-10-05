from typing import cast

import matplotlib.pyplot as plt
import numpy as np
import sqil_core as sqil
from laboneq.dsl.quantum import QPU
from laboneq.dsl.quantum.quantum_element import QuantumElement
from numpy.typing import ArrayLike
from sqil_core.experiment import ExperimentHandler
from sqil_core.experiment.instruments.rf_source import RfSource
from sqil_core.experiment.instruments.vna import VNA
from tqdm.auto import tqdm

from sqil_experiments.measurements.helpers.sqil_transmon.operations import (
    SqilTransmonOperations,
)
from sqil_experiments.measurements.helpers.sqil_transmon.qubit import SqilTransmon
from sqil_experiments.measurements.qu_spec import qu_spec_analysis

# from sqil_experiments.measurements.helpers.Rohde_Schwarz_ZNA26 import RohdeSchwarzZNA26
# from sqil_experiments.measurements.helpers.ZNB_taketo import RohdeSchwarzZNBChannel

VNA_IP = r"TCPIP0::192.168.1.203::inst0::INSTR"

import time


class CW_QuSpec(ExperimentHandler):
    exp_name = "cw_qubit_spectroscopy"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "frequencies": {
            "role": "x-axis",
            "unit": "Hz",
            "scale": 1e-9,
        },
    }

    def sequence(
        self,
        frequencies,
        bw=1e3,
        count=1,
        qu_ids=["q0"],
        *params,
        **kwargs,
    ):
        if len(qu_ids) > 1:
            raise ValueError("Only one qubit at the time is allowed")
        qubit = cast(SqilTransmon, self.qpu[qu_ids[0]])
        frequencies = frequencies[0]

        # VNA params
        start = qubit.parameters.readout_resonator_frequency
        stop = qubit.parameters.readout_resonator_frequency
        n_points = 1

        vna = cast(VNA, self.instruments.vna)
        vna.set_frequency_range(start, stop, n_points)
        vna.set_bandwidth(bw)
        vna.set_averages(count)

        drive = cast(RfSource, self.instruments.q0_drive)
        drive.turn_on()

        data = np.zeros_like(frequencies, dtype=complex)
        bar = tqdm(
            enumerate(frequencies),
            desc="Drive frequency",
            total=len(frequencies),
            leave=False,
        )
        for i, freq in bar:
            drive.set_frequency(freq)
            data[i] = vna.get_IQ_data()

        drive.turn_off()

        return data

    def analyze(self, path, *args, **kwargs):
        relevant_params = kwargs.get("relevant_params")
        if not relevant_params:
            kwargs["relevant_params"] = [
                "readout_power",
                "readout_acquire_bandwith",
                "readout_acquire_averages",
            ]
        return qu_spec_analysis(path=path, **kwargs)
