"""Unit mean energy Gray square constellations, with nearest-neighbor decisions."""
import numpy as np


def constellation(modulation):
    if modulation not in ("QPSK", "16QAM"):
        raise ValueError("Unsupported modulation")
    b = 2 if modulation == "QPSK" else 4
    labels = ((np.arange(2**b)[:, None] >> np.arange(b - 1, -1, -1)) & 1).astype(np.uint8)
    if b == 2:
        points = ((1 - 2 * labels[:, 0].astype(float))
                  + 1j * (1 - 2 * labels[:, 1].astype(float))) / np.sqrt(2)
    else:
        # Axis bits 00,01,11,10 map to -3,-1,+1,+3.
        levels = np.array([-3, -1, 3, 1])
        points = (levels[2 * labels[:, 0] + labels[:, 1]]
                  + 1j * levels[2 * labels[:, 2] + labels[:, 3]]) / np.sqrt(10)
    return points, labels


def modulate(bits, modulation="QPSK"):
    points, labels = constellation(modulation)
    bits = np.asarray(bits)
    b = labels.shape[1]
    if bits.ndim != 1 or bits.size % b or not np.all((bits == 0) | (bits == 1)):
        raise ValueError("Expected binary vector containing complete symbols")
    indices = bits.reshape(-1, b) @ (2 ** np.arange(b - 1, -1, -1))
    return points[indices]


def demodulate(symbols, modulation="QPSK"):
    points, labels = constellation(modulation)
    nearest = np.argmin(abs(np.asarray(symbols).reshape(-1, 1) - points[None, :])**2, axis=1)
    return labels[nearest].reshape(-1)
