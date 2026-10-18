## Result

Implement an executable 1×4 SIMO OFDM communication chain and single-source MUSIC direction finding on the same received spatial-channel waveform. Include Gray QPSK/16-QAM, convolutional AWGN/Rayleigh/spatial channels, pilot LS with interpolation, perfect-CSI references, MRC, deterministic experiments, configuration validation and detailed signal/energy assumptions.

## Numerical validation

- 40 local pytest cases passed, including noiseless recovery, AWGN theory normalization, MRC diversity and shared-data MUSIC.
- Full 0–30 dB suite generated seven figures and raw JSON/NPZ results with 240 frames (552,960 QPSK bits) per communication point and 160 trials per sensing point.
- At 10 dB transmit Eb/N0, baseline pilot-LS BER was 0.067587 (SISO) and 0.00084635 (1×4 SIMO).
- MUSIC RMSE was 0.1005° at 10 dB sample SNR with an off-grid 23.37° source.
- GitHub Actions is configured for Python 3.11/3.13 tests and a full-pipeline smoke run; hosted status must be reviewed after publication.

## Scope and limits

Known timing, block-static fading, one-source narrowband ULA sensing and uncoded hard decisions. Independent branch Rayleigh diversity and shared-angle spatial sensing are distinct declared channel experiments. Pilot interpolation error floors and zero-error statistical limitations are documented. No practical acquisition, multiple-angle coherent-path recovery, range-Doppler sensing or hardware performance claims.

Please review before merging into the default branch.
