# Resume-ready project entry

**SIMO OFDM Receiver with Shared-Waveform Direction Finding** | Python, NumPy, SciPy, Matplotlib, pytest

- Built a modular 1×4 SIMO OFDM link with Gray QPSK/16-QAM, time-domain Rayleigh multipath, pilot-assisted LS channel estimation and maximum-ratio combining.
- Evaluated SISO/SIMO and estimated/perfect-CSI receivers over 0–30 dB; measured pilot-LS BER of 8.46×10⁻⁴ versus 6.76×10⁻² for SISO at 10 dB using 552,960 bits per point.
- Integrated MUSIC direction finding on the same received array data, achieving 0.10° AoA RMSE at 10 dB sample SNR across 160 trials; validated the signal chain with 40 automated numerical tests.

Use these only after you have run the project and can explain its assumptions. The BER comparison uses independent branch Rayleigh fading, while AoA uses a single shared-angle spatial channel. Both are simulations. Do not describe this work as hardware, radar range-Doppler sensing, a publication, or aerospace field validation.

## Interview discussion prompts

- Why is the waveform FFT unitary while the channel-response FFT is unnormalized?
- How do pilots, null bins and the cyclic prefix change the meaning of Eb/N0?
- Why does the long-delay case have poor pilot-LS BER even though every tap fits inside the CP?
- What is the difference between MRC array gain and independent fading diversity?
- Why does one shared-angle multipath channel support ordinary MUSIC, while multiple coherent angles need additional processing?
- Why do zero observed errors in 240 fading frames not certify ultra-low BER?
