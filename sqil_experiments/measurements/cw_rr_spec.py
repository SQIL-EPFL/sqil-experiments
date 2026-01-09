from typing import cast

import matplotlib.pyplot as plt
import numpy as np
from sqil_core.experiment import ExperimentHandler
from sqil_core.experiment.instruments.vna import VNA

from sqil_experiments.measurements.rr_spec import rr_spec_analysis


class CW_RRSpec(ExperimentHandler):
    exp_name = "cw_resonator_spectroscopy"
    db_schema = {
        "data": {"role": "data", "unit": "V", "scale": 1e3},
        "readout_resonator_frequency": {
            "role": "x-axis",
            "unit": "Hz",
            "scale": 1e-9,
        },
    }

    def sequence(
        self,
        readout_resonator_frequency: list,
        qu_ids=["q0"],
        *params,
        **kwargs,
    ):
        if len(qu_ids) > 1:
            raise ValueError("Only one qubit at the time is allowed")
        qubit = self.qpu[qu_ids[0]]
        readout_resonator_frequency = np.array(readout_resonator_frequency)

        if readout_resonator_frequency.ndim > 1:
            readout_resonator_frequency = readout_resonator_frequency[0]

        start = readout_resonator_frequency[0]
        stop = readout_resonator_frequency[-1]
        n_points = len(readout_resonator_frequency)

        vna = cast(VNA, self.instruments.vna)
        vna.set_frequency_range(start, stop, n_points)

        return self.instruments.vna.get_IQ_data()

    def analyze(self, path, *args, **kwargs):
        relevant_params = kwargs.get("relevant_params")
        if not relevant_params:
            kwargs["relevant_params"] = [
                "readout_power",
                "readout_acquire_bandwith",
                "readout_acquire_averages",
            ]
        return rr_spec_analysis(path=path, **kwargs)
