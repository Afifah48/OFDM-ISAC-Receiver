from dataclasses import replace

import numpy as np
import pytest
from scipy.special import erfc

from ofdm_isac.channel.models import propagate, steering
from ofdm_isac.evaluation.experiments import error_summary
from ofdm_isac.receiver.processing import decode_waveform, estimate_channel, mrc, receive
from ofdm_isac.sensing.music import music
from ofdm_isac.transmitter.modulation import constellation, demodulate, modulate
from ofdm_isac.transmitter.ofdm import encode_grid, transmit
from ofdm_isac.utils.config import Config, load_config


@pytest.mark.parametrize("mod", ["QPSK", "16QAM"])
def test_modulation_all_labels_and_gray_neighbors(mod):
    points, labels = constellation(mod)
    np.testing.assert_array_equal(demodulate(modulate(labels.ravel(), mod), mod), labels.ravel())
    assert np.mean(abs(points)**2) == pytest.approx(1)
    distance = abs(points[:, None] - points[None, :])
    nearest = np.min(distance[distance > 0])
    i, j = np.where(np.isclose(distance, nearest))
    assert np.all(np.sum(labels[i] != labels[j], axis=1) == 1)


@pytest.mark.parametrize("cp", [0, 16])
def test_fft_ifft_and_prefix(cp):
    c = replace(Config(), cp=cp, tap_delays=(0,), tap_powers_db=(0,))
    rng = np.random.default_rng(1)
    grid = rng.normal(size=(c.n_symbols, c.n_fft)) + 1j * rng.normal(size=(c.n_symbols, c.n_fft))
    wave = encode_grid(grid, cp)
    np.testing.assert_allclose(decode_waveform(wave[None, :], c)[0], grid, atol=2e-15)
    if cp:
        block = wave.reshape(c.n_symbols, -1)
        np.testing.assert_array_equal(block[:, :cp], block[:, -cp:])
    assert np.sum(abs(np.fft.ifft(grid, norm="ortho"))**2) == pytest.approx(np.sum(abs(grid)**2))


def test_grid_allocation_and_pilot_extraction():
    c = Config()
    tx = transmit(c, np.random.default_rng(3))
    assert len(c.active_signed) == 52
    assert len(c.pilots_signed) == 16
    assert len(c.data_signed) == 36
    assert set(c.pilots_signed).isdisjoint(c.data_signed)
    np.testing.assert_array_equal(tx.grid[:, c.pilots_signed % c.n_fft], 1)
    np.testing.assert_array_equal(tx.grid[:, np.setdiff1d(np.arange(c.n_fft), c.active_signed % c.n_fft)], 0)


@pytest.mark.parametrize("mod", ["QPSK", "16QAM"])
@pytest.mark.parametrize("antennas", [1, 4])
@pytest.mark.parametrize("channel", ["awgn", "rayleigh", "spatial"])
def test_noiseless_bit_recovery(mod, antennas, channel):
    c = replace(Config(), modulation=mod, n_rx=antennas, channel=channel)
    rng = np.random.default_rng(48)
    tx = transmit(c, rng)
    obs = propagate(tx.waveform, c, rng)
    perfect = receive(obs, c, perfect_csi=True)
    np.testing.assert_array_equal(perfect.bits, tx.bits)
    np.testing.assert_allclose(perfect.grid, obs.response[:, None, :] * tx.grid[None, :, :], atol=3e-15)
    # LS + interpolation is exact for a flat channel; multipath is approximate.
    if channel == "awgn":
        np.testing.assert_array_equal(receive(obs, c).bits, tx.bits)


def test_known_channel_ls_linear_interpolation():
    c = Config()
    h = np.zeros((c.n_rx, c.n_symbols, c.n_fft), complex)
    for r in range(c.n_rx):
        h[r, :, c.active_signed % c.n_fft] = (1 + r + (0.01 + 0.02j) * c.active_signed)[:, None]
    tx = transmit(c, np.random.default_rng(4))
    estimate = estimate_channel(h * tx.grid, c)
    np.testing.assert_allclose(estimate[..., c.active_signed % c.n_fft], h[..., c.active_signed % c.n_fft], atol=2e-15)


@pytest.mark.parametrize("antennas", [1, 4])
def test_awgn_theory_with_overhead(antennas):
    c = replace(Config(), channel="awgn", n_rx=antennas, n_symbols=3000)
    rng = np.random.default_rng(32)
    tx = transmit(c, rng)
    db = 0
    obs = propagate(tx.waveform, c, rng, ebn0_db=db)
    rx = receive(obs, c, perfect_csi=True)
    measured = np.mean(rx.bits != tx.bits)
    theory = 0.5 * erfc(np.sqrt(antennas * 10**(db / 10) / (2 * c.eb_tx)))
    standard_error = np.sqrt(theory * (1 - theory) / len(tx.bits))
    assert abs(measured - theory) < 6 * standard_error


def test_mrc_rayleigh_diversity():
    rng = np.random.default_rng(45)
    c = replace(Config(), n_symbols=8, tap_delays=(0,), tap_powers_db=(0,))
    counts = np.zeros(2, int)
    for _ in range(250):
        tx = transmit(c, rng)
        obs = propagate(tx.waveform, c, rng, ebn0_db=8)
        y = decode_waveform(obs.waveform, c)
        for i, r in enumerate([1, 4]):
            symbols = mrc(y[:r], obs.response[:r, None, :])[:, c.data_signed % c.n_fft]
            counts[i] += np.count_nonzero(demodulate(symbols) != tx.bits)
    assert counts[1] < counts[0] / 5


def test_music_known_angle_and_sign():
    rng = np.random.default_rng(2)
    x = rng.normal(size=400) + 1j * rng.normal(size=400)
    for angle in [-37.2, 0, 23.4]:
        result = music(steering(angle, 4)[:, None] * x)
        assert result.angle_deg == pytest.approx(angle, abs=0.051)


def test_music_same_observation_as_communications():
    rng = np.random.default_rng(2)
    c = replace(Config(), channel="spatial")
    tx = transmit(c, rng)
    obs = propagate(tx.waveform, c, rng, snr_db=25)
    rx = receive(obs, c)
    result = music(rx.grid[:, :, c.active_signed % c.n_fft].reshape(c.n_rx, -1))
    assert abs(result.angle_deg - c.angle_deg) < 0.2
    assert np.mean(rx.bits != tx.bits) < 0.01


def test_repeatable():
    c = Config()
    def once():
        rng = np.random.default_rng(c.seed)
        tx = transmit(c, rng)
        return propagate(tx.waveform, c, rng, ebn0_db=8).waveform
    np.testing.assert_array_equal(once(), once())


def test_offset_oracle_correction():
    c = replace(Config(), channel="awgn", cfo=0.17, timing_offset=5)
    rng = np.random.default_rng(48)
    tx = transmit(c, rng)
    obs = propagate(tx.waveform, c, rng)
    obs.waveform = obs.waveform[:, c.timing_offset:] * np.exp(-2j * np.pi * c.cfo * np.arange(len(tx.waveform)) / c.n_fft)
    np.testing.assert_array_equal(receive(obs, c).bits, tx.bits)


@pytest.mark.parametrize("kwargs", [{"cp": -1}, {"n_fft": 63}, {"n_rx": 0}, {"modulation": "BPSK"},
    {"tap_delays": (0, 18)}, {"channel": "unknown"}, {"spacing_wavelengths": 0.7},
    {"tap_delays": (0, 0, 2)}, {"tap_powers_db": (0, float('nan'), -8)}, {"n_symbols": 2.5}])
def test_invalid_configs(kwargs):
    with pytest.raises(ValueError):
        replace(Config(), **kwargs)


def test_yaml_config_and_unknown_keys(tmp_path):
    assert load_config("configs/baseline.yaml").n_rx == 4
    path = tmp_path / "bad.yaml"
    path.write_text("unknown: 3")
    with pytest.raises(ValueError):
        load_config(path)


def test_zero_error_reporting():
    result = error_summary([0] * 100, 1000)
    assert result["ber"] == 0
    assert result["zero_error_frame_event_upper_95"] > result["zero_error_iid_bit_upper_95"] > 0


def test_noiseless_flat_ls_recovery():
    c = replace(Config(), tap_delays=(0,), tap_powers_db=(0,))
    rng = np.random.default_rng(18)
    tx = transmit(c, rng)
    np.testing.assert_array_equal(receive(propagate(tx.waveform, c, rng), c).bits, tx.bits)


@pytest.mark.parametrize("modulation", ["QPSK", "16QAM"])
def test_exact_expected_energy_with_fixed_pilots(modulation):
    c = replace(Config(), modulation=modulation, n_symbols=8000)
    tx = transmit(c, np.random.default_rng(123))
    measured = np.sum(abs(tx.waveform)**2) / c.n_symbols
    assert measured == pytest.approx(c.expected_symbol_energy, rel=0.004)
    assert c.expected_symbol_energy == pytest.approx(64.3419617694719)
    assert c.eb_tx == pytest.approx(c.expected_symbol_energy / (36 * c.bits_per_symbol))
