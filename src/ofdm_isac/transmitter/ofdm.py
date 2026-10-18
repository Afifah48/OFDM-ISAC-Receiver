"""Time-domain OFDM with explicit data, pilot, guard and DC allocation."""
from dataclasses import dataclass

import numpy as np

from .modulation import modulate


@dataclass
class Transmission:
    bits: np.ndarray
    grid: np.ndarray
    waveform: np.ndarray


def encode_grid(grid, cp):
    samples = np.fft.ifft(grid, axis=-1, norm="ortho")
    prefix = samples[..., -cp:] if cp else samples[..., :0]
    return np.concatenate([prefix, samples], axis=-1).reshape(-1)


def transmit(config, rng):
    n_bits = config.n_symbols * len(config.data_signed) * config.bits_per_symbol
    bits = rng.integers(0, 2, n_bits, dtype=np.uint8)
    grid = np.zeros((config.n_symbols, config.n_fft), complex)
    grid[:, config.pilots_signed % config.n_fft] = 1 + 0j
    grid[:, config.data_signed % config.n_fft] = modulate(bits, config.modulation).reshape(config.n_symbols, -1)
    return Transmission(bits, grid, encode_grid(grid, config.cp))
