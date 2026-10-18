"""Optional oracle offset correction experiment, not a practical synchronizer."""
from dataclasses import replace
import json

import numpy as np

from ofdm_isac.channel.models import Observation, propagate
from ofdm_isac.receiver.processing import receive
from ofdm_isac.transmitter.ofdm import transmit
from ofdm_isac.utils.config import Config


def main():
    rng = np.random.default_rng(48)
    records = []
    for cfo, timing in [(0, 0), (0.15, 0), (0, 5), (0.15, 5)]:
        config = replace(Config(), channel="awgn", cfo=cfo, timing_offset=timing)
        tx = transmit(config, rng)
        obs = propagate(tx.waveform, config, rng, ebn0_db=20)
        raw = receive(obs, config)
        corrected = obs.waveform[:, timing:] * np.exp(-2j * np.pi * cfo * np.arange(len(tx.waveform)) / config.n_fft)
        oracle = receive(Observation(corrected, obs.response, obs.taps, obs.noise_variance), config)
        records.append({"cfo_subcarrier_spacings": cfo, "timing_samples": timing,
                        "raw_ber": float(np.mean(tx.bits != raw.bits)),
                        "oracle_corrected_ber": float(np.mean(tx.bits != oracle.bits))})
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
