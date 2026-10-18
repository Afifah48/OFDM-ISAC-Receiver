"""Validated system parameters. Signed subcarrier indices use FFT ordering."""
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import yaml


@dataclass(frozen=True)
class Config:
    n_fft: int = 64
    cp: int = 16
    n_symbols: int = 32
    modulation: str = "QPSK"
    n_rx: int = 4
    pilot_stride: int = 4
    tap_delays: tuple = (0, 2, 4)
    tap_powers_db: tuple = (0, -4, -8)
    channel: str = "rayleigh"
    angle_deg: float = 23.4
    spacing_wavelengths: float = 0.5
    cfo: float = 0.0
    timing_offset: int = 0
    seed: int = 48

    def __post_init__(self):
        for name in ("n_fft", "cp", "n_symbols", "n_rx", "pilot_stride", "timing_offset", "seed"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{name} must be an integer")
        if self.n_fft < 16 or self.n_fft % 2 or not 0 <= self.cp < self.n_fft:
            raise ValueError("FFT must be even and >=16; CP must be in [0,N)")
        if self.n_rx < 1 or self.n_symbols < 1 or self.pilot_stride < 2:
            raise ValueError("Positive antennas/symbols and pilot_stride >=2 required")
        if self.modulation not in ("QPSK", "16QAM"):
            raise ValueError("modulation must be QPSK or 16QAM")
        if self.channel not in ("awgn", "rayleigh", "spatial"):
            raise ValueError("Unknown channel")
        if not self.tap_delays or len(self.tap_delays) != len(self.tap_powers_db):
            raise ValueError("Tap delays/powers must have matching nonempty lengths")
        if any(not isinstance(d, int) or d < 0 or d > self.cp for d in self.tap_delays):
            raise ValueError("Integer tap delays must be in [0,CP]")
        if len(set(self.tap_delays)) != len(self.tap_delays):
            raise ValueError("Tap delays must be distinct")
        if not np.all(np.isfinite(self.tap_powers_db)):
            raise ValueError("Finite tap powers required")
        if not -89 <= self.angle_deg <= 89 or not 0 < self.spacing_wavelengths <= 0.5:
            raise ValueError("Angle in [-89,89], spacing in (0,0.5] wavelengths required")
        if not np.isfinite(self.cfo) or self.timing_offset < 0 or self.seed < 0:
            raise ValueError("Invalid offset or seed")
        if len(self.data_signed) == 0:
            raise ValueError("No data subcarriers")

    @property
    def active_signed(self):
        edge = int(self.n_fft * 26 / 64)
        return np.r_[np.arange(-edge, 0), np.arange(1, edge + 1)]

    @property
    def pilots_signed(self):
        # Each side of DC includes both endpoints: interpolation never extrapolates.
        parts = []
        for side in (self.active_signed[self.active_signed < 0], self.active_signed[self.active_signed > 0]):
            parts.append(np.unique(np.r_[side[::self.pilot_stride], side[-1]]))
        return np.concatenate(parts)

    @property
    def data_signed(self):
        return np.setdiff1d(self.active_signed, self.pilots_signed)

    @property
    def bits_per_symbol(self):
        return 2 if self.modulation == "QPSK" else 4

    @property
    def expected_symbol_energy(self):
        """Exact ensemble energy including the fixed pilots' coherent CP energy."""
        pilot_grid = np.zeros(self.n_fft, complex)
        pilot_grid[self.pilots_signed % self.n_fft] = 1
        pilot_wave = np.fft.ifft(pilot_grid, norm="ortho")
        pilot_prefix_energy = np.sum(abs(pilot_wave[-self.cp:])**2) if self.cp else 0.0
        return float(len(self.active_signed) + len(self.data_signed) * self.cp / self.n_fft
                     + pilot_prefix_energy)

    @property
    def eb_tx(self):
        """Expected total transmit energy / information bit, including CP/pilots."""
        return self.expected_symbol_energy / (len(self.data_signed) * self.bits_per_symbol)


def load_config(path):
    values = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(values, dict) or set(values) - {f.name for f in fields(Config)}:
        raise ValueError("Expected a mapping of known configuration keys")
    return Config(**values)
