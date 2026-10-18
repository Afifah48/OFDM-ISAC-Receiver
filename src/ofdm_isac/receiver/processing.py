"""Perfect/oracle timing baseline; offsets are not estimated by this module."""
from dataclasses import dataclass

import numpy as np

from ofdm_isac.transmitter.modulation import demodulate


def decode_waveform(waveform, config, start_sample=0):
    length = config.n_symbols * (config.n_fft + config.cp)
    waveform = np.asarray(waveform)
    if waveform.ndim != 2 or start_sample < 0 or waveform.shape[1] < start_sample + length:
        raise ValueError("Insufficient array samples or invalid start")
    blocks = waveform[:, start_sample:start_sample + length].reshape(waveform.shape[0], config.n_symbols, -1)
    return np.fft.fft(blocks[..., config.cp:], axis=-1, norm="ortho")


def estimate_channel(y, config):
    """LS at unit pilots, linear complex interpolation separately across DC."""
    estimate = np.zeros_like(y)
    for negative in (True, False):
        active = config.active_signed[(config.active_signed < 0) == negative]
        pilots = config.pilots_signed[(config.pilots_signed < 0) == negative]
        for r in range(y.shape[0]):
            for m in range(y.shape[1]):
                values = y[r, m, pilots % config.n_fft]
                estimate[r, m, active % config.n_fft] = np.interp(active, pilots, values)
    return estimate


def mrc(y, h, epsilon=1e-12):
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    return np.sum(h.conj() * y, axis=0) / (np.sum(abs(h)**2, axis=0) + epsilon)


@dataclass
class Reception:
    bits: np.ndarray
    symbols: np.ndarray
    grid: np.ndarray
    csi: np.ndarray


def receive(observation, config, perfect_csi=False, start_sample=0):
    y = decode_waveform(observation.waveform, config, start_sample)
    h = (np.broadcast_to(observation.response[:, None, :], y.shape).copy()
         if perfect_csi else estimate_channel(y, config))
    equalized = mrc(y, h)[:, config.data_signed % config.n_fft]
    return Reception(demodulate(equalized, config.modulation), equalized, y, h)
