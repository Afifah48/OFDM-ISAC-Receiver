# Validation record

Local validation on 2026-10-18 (Asia/Calcutta), Python 3.13.5, isolated `.venv`.

## Commands executed

```text
python -m pip install -e ".[dev]"
python -m pytest -q
ofdm-isac --config configs/baseline.yaml --frames 240 --trials 160 --step 5 --output results
python scripts/impairments.py
python -m pip check
```

The full experiment suite was executed, not inferred from tests. `results/metrics.json` includes exact configuration, Python/NumPy versions, run duration, errors, bit/frame counts, frame-bootstrap intervals, MSE, trial-level AoA estimates and communication statistics from the sensing receptions. `requirements-lock.txt` records the tested Python 3.13 environment; use the pyproject dependency ranges on other Python versions.

## Tests

40 tests passed locally. Parameterized tests include 12 noiseless recovery cases across QPSK/16-QAM, one/four receive antennas and AWGN/Rayleigh/spatial channels. Perfect CSI is used for exact frequency-selective recovery. Flat channels also verify pilot-LS recovery. The synthetic interpolation test constructs a channel that is exactly linear across signed bins, isolating the interpolation operation from the approximation error of a real multipath frequency response.

AWGN theory tests use 216,000 bits each for one and four antennas at 0 dB transmit Eb/N0. With QPSK perfect CSI, decision-axis noise is independent and a binomial standard-error comparison is valid. Each measured BER must lie within six standard errors of the overhead-corrected reference. This is a deterministic regression check with a fixed seed, not a statement that all Monte Carlo points must match theory exactly.

The MRC diversity test samples 250 independent flat Rayleigh frames and requires four-branch perfect-CSI error count to be below one fifth of the matched first-branch SISO count. MUSIC tests check known positive and negative angles and verify that communication FFT samples produce the declared AoA. Offset correction removes only known offsets and is labeled oracle-assisted.

## Measured engineering findings

- At 10 dB transmit Eb/N0, baseline pilot-LS SISO/SIMO errors are 37,373/468 out of 552,960 bits each. Perfect-CSI SIMO has 90 errors.
- At 15 dB, pilot-LS SIMO has nine errors in three frames. This is too few error events for a precise low-BER claim.
- At 20–30 dB, no baseline SIMO errors were observed. Their iid-bit bounds must not be applied to correlated fading errors; independent-frame bounds and explicit sample counts are retained.
- Data-subcarrier CSI MSE is 0.05364 at 10 dB sample SNR and 0.007663 at 30 dB. Linear interpolation bias remains as pilot noise decreases.
- The [0,6,12]-sample Rayleigh stress channel fits the 16-sample CP, yet its four-antenna pilot-LS BER at 10 dB is 0.02236. CP validity and CSI interpolation accuracy are distinct requirements.
- AoA RMSE is 0.1005° at 10 dB and 0.03162° at 30 dB sample SNR across 160 trials per point, approaching the 0.03° scan-grid floor for the 23.37° source.

## Technical review

Checked unitary transform energy, convolution/DFT scaling, CP length versus tap support, signed pilot indexing, complex interpolation, steering phase sign, equal per-branch noise variance, transmit-referenced Eb/N0 overhead, and distinction between array gain and fading diversity. All seven generated figures were visually inspected for labels, legend, units and consistency with the recorded metrics.

The implementation has no practical synchronization, multiple-angle coherent multipath recovery, time-varying path-specific Doppler, FEC or hardware tests. CI is configured for Python 3.11 and 3.13, but local verification was on 3.13.5; hosted CI must be checked separately after upload.
