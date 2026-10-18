"""Narrowband ULA MUSIC; spatial channel must have one shared arrival angle."""
from dataclasses import dataclass

import numpy as np


@dataclass
class MusicResult:
    angle_deg: float
    angles: np.ndarray
    spectrum_db: np.ndarray
    eigenvalues: np.ndarray
    covariance: np.ndarray


def music(snapshots, spacing=0.5, angles=None):
    """snapshots shape is (antennas, observations); assumes one source."""
    x = np.asarray(snapshots)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < x.shape[0]:
        raise ValueError("MUSIC requires >=2 antennas and >=N_rx snapshots")
    if not 0 < spacing <= 0.5 or not np.all(np.isfinite(x)):
        raise ValueError("Invalid spacing or samples")
    angles = np.linspace(-89, 89, 1781) if angles is None else np.asarray(angles)
    if angles.ndim != 1 or len(angles) < 3 or np.any(np.diff(angles) <= 0):
        raise ValueError("Angle grid must be increasing with >=3 points")
    covariance = x @ x.conj().T / x.shape[1]
    eigenvalues, vectors = np.linalg.eigh(covariance)
    noise = vectors[:, :-1]
    a = np.exp(-2j * np.pi * spacing * np.arange(x.shape[0])[:, None] * np.sin(np.deg2rad(angles)))
    denom = np.maximum(np.sum(abs(noise.conj().T @ a)**2, axis=0), 1e-15)
    db = -10 * np.log10(denom / denom.min())
    peak = np.argmin(denom)
    return MusicResult(float(angles[peak]), angles, db, eigenvalues, covariance)
