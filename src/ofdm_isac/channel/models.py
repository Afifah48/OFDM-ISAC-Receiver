"""Block fading channels. No per-realization gain normalization."""
from dataclasses import dataclass

import numpy as np


def steering(angle_deg, n_rx, spacing=0.5):
    return np.exp(-2j * np.pi * spacing * np.arange(n_rx) * np.sin(np.deg2rad(angle_deg)))


def sample_taps(config, rng):
    if config.channel == "awgn":
        return np.ones((config.n_rx, 1), complex)
    power = 10.0 ** (np.array(config.tap_powers_db) / 10)
    power /= power.sum()
    count = 1 if config.channel == "spatial" else config.n_rx
    gains = (rng.normal(size=(count, len(power))) + 1j * rng.normal(size=(count, len(power)))) * np.sqrt(power / 2)
    taps = np.zeros((count, max(config.tap_delays) + 1), complex)
    taps[:, config.tap_delays] = gains
    if config.channel == "spatial":
        taps = steering(config.angle_deg, config.n_rx, config.spacing_wavelengths)[:, None] * taps
    return taps


@dataclass
class Observation:
    waveform: np.ndarray
    response: np.ndarray
    taps: np.ndarray
    noise_variance: float


def propagate(waveform, config, rng, ebn0_db=None, snr_db=None, taps=None):
    """SNR is referenced to ensemble unit-gain time-domain signal power.

    Eb/N0 is total transmitter energy per information bit / complex noise variance.
    Passing neither power ratio produces a noiseless observation.
    """
    if ebn0_db is not None and snr_db is not None:
        raise ValueError("Choose Eb/N0 or SNR, not both")
    taps = sample_taps(config, rng) if taps is None else np.asarray(taps)
    if taps.ndim != 2 or taps.shape[0] != config.n_rx or taps.shape[1] - 1 > config.cp:
        raise ValueError("Tap matrix must match array and fit CP")
    received = np.stack([np.convolve(waveform, h)[:len(waveform)] for h in taps])
    received *= np.exp(2j * np.pi * config.cfo * np.arange(len(waveform)) / config.n_fft)
    if config.timing_offset:
        received = np.pad(received, ((0, 0), (config.timing_offset, 0)))
    if ebn0_db is not None:
        variance = config.eb_tx * 10.0 ** (-ebn0_db / 10)
    elif snr_db is not None:
        variance = config.expected_symbol_energy / (config.n_fft + config.cp) * 10.0 ** (-snr_db / 10)
    else:
        variance = 0.0
    noise = np.sqrt(variance / 2) * (rng.normal(size=received.shape) + 1j * rng.normal(size=received.shape))
    # H is the ordinary DFT of h: the convolution theorem supplies this scaling
    # even though the waveform transforms themselves are unitary.
    response = np.fft.fft(taps, n=config.n_fft, axis=-1)
    return Observation(received + noise, response, taps, variance)
