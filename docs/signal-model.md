# Signal model and engineering assumptions

## OFDM and framing

For symbol m, N=64 and C=16 by default:

$$x_m[n]=\frac{1}{\sqrt N}\sum_{k=0}^{N-1} X_m[k]e^{j2\pi kn/N}.$$

Both waveform transforms use `norm="ortho"`. The last C useful samples precede each symbol. There are 52 active bins: signed indices -26…-1 and 1…26, mapped with `k % N`. DC and the other 11 bins are zero. Each side of DC has pilots every four bins plus its final endpoint, giving 16 pilots and 36 data bins. All pilots are known +1. QPSK has two bits per symbol; 16-QAM has four. Constellations have unit *ensemble* average energy. A random 16-QAM frame need not have exactly unit empirical symbol energy.

The receiver knows the first symbol boundary and symbol count. There is no acquisition preamble, timing estimator or CFO estimator. `start_sample` can apply known/oracle timing. The impairment script demonstrates known-offset compensation independently; it is not practical synchronization.

The channel is constant over a frame and independently redrawn between frames:

$$y_r[n]=\sum_\ell h_r[\ell]x[n-\ell]+w_r[n],\quad w_r\sim\mathcal{CN}(0,\sigma_w^2).$$

Linear convolution is applied to the serialized waveform, including prefixes. The retained output has the same length as the transmitted waveform; the last convolution tail is unnecessary for the useful FFT windows. Maximum delay must be no greater than C, so channel length is at most C+1; the baseline's maximum delay is 4, strictly shorter than C. With correct timing, zero CFO, and a channel constant over each symbol:

$$Y_r[m,k]=H_r[k]X_m[k]+W_r[m,k],\quad H_r[k]=\sum_\ell h_r[\ell]e^{-j2\pi k\ell/N}.$$

**H is an unnormalized FFT of the taps**, despite the unitary waveform FFT/IFFT. Replacing it with a unitary tap FFT would incorrectly introduce a factor of sqrt(N). Noise variance is unchanged by the unitary FFT.

## Channels and diversity

`awgn`: every antenna has h[0]=1. Four antennas provide coherent array gain from independent receiver noise, but no fading diversity.

`rayleigh`: each antenna and delay has an independent circular Gaussian gain. Tap powers 10^(p/10) are normalized to sum to one in expectation. Individual frame gains are **not** normalized: deep fades and gain fluctuations are physically retained. SISO comparisons use antenna zero of the same four-antenna observation. The four-antenna model assumes uncorrelated branch fading; this is a reference diversity model, not a geometry-derived assertion for every half-wavelength array.

`spatial`: h_r[ell]=a_r(theta) g[ell], with a common Rayleigh delay profile and one far-field direction. All delays share the same direction. This gives rank-one spatial signal covariance, array gain and frequency selectivity, but **not four independent fading branches**. This deliberately restricted sensing model supports conventional single-source MUSIC. Independent-branch Rayleigh channels have no single physical AoA and are not fed to the direction estimator.

All branches have equal independent white receiver noise. CFO is specified in subcarrier spacings and multiplies the whole received signal by exp(j2*pi*cfo*n/N) before AWGN. Timing offset is a nonnegative sample delay. Neither models path-specific Doppler or time-varying delay taps.

## Noise and energy conventions

Let A=52 active bins, D=36 data bins and b=log2(M). Fixed +1 pilots combine coherently in time. Let p[n] be the unitary IFFT of the pilot-only grid. Independent zero-mean data symbols contribute D/N expected energy per time sample. Expected useful OFDM energy is A; exact expected prefix energy is DC/N + E_p,CP, where E_p,CP is the sum of |p[n]|² over the last C samples. Thus

$$E_{\mathrm{OFDM}}=A+DC/N+E_{p,CP},\qquad E_{b,tx}=\frac{E_{\mathrm{OFDM}}}{Db}.$$

For the baseline, E_p,CP=3.34196176947, E_OFDM=64.34196176947 and QPSK E_b,tx=0.89363835791 in the chosen discrete-time energy units. The common A*(1+C/N)=65 approximation overcounts the actual expected energy for these fixed pilots. The implementation computes pilot prefix energy exactly; Monte Carlo energy tests cover QPSK and 16-QAM. For requested gamma_b=10^(EbN0_dB/10), set sigma_w^2=E_b,tx/gamma_b. This is a transmit-referenced convention; fading does not trigger noise rescaling and receive-array gain is not included in Eb.

The *data constellation* Es is one, so Es/N0=1/sigma_w^2. Useful data-only bit energy is Es/b; therefore its Eb/N0 is gamma_b/[E_OFDM/D]. The overhead factor is 64.34196176947/36=1.78727671582, or 2.52191798 dB. A theoretical QPSK reference must include this penalty:

$$P_b=\tfrac12\operatorname{erfc}\!\left(\sqrt{\frac{1}{2\sigma_w^2}}\right)
=\tfrac12\operatorname{erfc}\!\left(\sqrt{\frac{\gamma_b}{E_{\mathrm{OFDM}}/D}}\right).$$

With R identical unit-gain AWGN branches and perfect CSI, multiply the argument under the square root by R. These curves are not Rayleigh fading references and do not account for noisy pilot estimates.

The SNR axis in CSI and AoA experiments is ensemble unit-gain average sample SNR:

$$\gamma_s=\frac{E_{\mathrm{OFDM}}/(N+C)}{\sigma_w^2},\qquad
\gamma_s=\gamma_b\frac{Db}{N+C}.$$

It averages the full waveform including CP and null-bin dilution; for QPSK the conversion is SNR_dB=EbN0_dB+10log10(72/80). Realized post-channel SNR varies with fading. `propagate` accepts either `ebn0_db` or `snr_db`, never both. Frame energy is not measured and renormalized to hide overhead or fading.

## LS channel estimation and combining

At pilots, Hhat=Y/Xp=Y because Xp=1. Real and imaginary components are linearly interpolated across signed subcarriers independently on each side of DC. Endpoints are pilots, so no extrapolation is needed. Guards and DC are unused. Each OFDM symbol is estimated separately, with no temporal averaging; pilot noise and interpolation bias are visible in the results.

$$\hat X[m,k]=\frac{\sum_r\hat H_r^*[m,k]Y_r[m,k]}{\sum_r|\hat H_r[m,k]|^2+\epsilon},\qquad\epsilon=10^{-12}.$$

The epsilon prevents division by zero in deep/null channels; it is a numerical floor, not a noise-power parameter. This is normalized maximum-ratio combining/zero-forcing scalar equalization for one transmit stream. LMMSE with a unit-variance symbol prior and known equal branch noise would instead add sigma_w^2 to the denominator. No interference covariance or MMSE receiver is implemented. Perfect CSI uses the actual DFT of the sampled taps and is an oracle reference.

## MUSIC and array geometry

The ULA lies along the x-axis; theta is measured from broadside in the x-y plane, restricted to [-89,89] degrees. Antenna r is at r*d. The phase convention in both the channel and scan is

$$a_r(\theta)=e^{-j2\pi r(d/\lambda)\sin\theta}.$$

Spacing is dimensionless d/lambda, default 0.5. No physical carrier or sample rate is needed for this normalized simulation. One illustrative interpretation is fc=2.4 GHz (lambda approximately 0.125 m, d approximately 0.0625 m) and fs=1 MHz (delay samples 1 microsecond); these are not hardware measurements. The phase model assumes a far-field narrowband array: bandwidth times aperture / wave speed must be much less than one. It neglects beam squint, coupling and calibration error.

The sensing suite uses **exactly the noisy FFT array data used for bit recovery**, before channel equalization or combining. Stack all active bins over eight OFDM symbols: Z has shape R x (8*52)=4 x 416. Pilots are included, guards/DC omitted. The actual angle is 23.37 degrees, deliberately off the 0.1-degree scan grid.

$$\hat R=ZZ^H/K,\quad P(\theta)=\frac{1}{\|E_n^Ha(\theta)\|^2}.$$

`eigh` returns ascending eigenvalues. The first R-1 eigenvectors span the noise subspace under the declared one-source model. A bounded denominator avoids numerical infinities; the maximum spectrum value defines the estimate. The plotted spectrum is normalized to a 0 dB maximum. The covariance is an uncentered second moment, appropriate for the shared rank-one waveform including deterministic pilots.

Each trial draws fresh bits, taps and noise. Frequency snapshots share the channel; they are not 416 independent fading realizations. Sensing records also include bit errors from the same reception. No separately invented radar data are used.

MUSIC assumes a known source count of one, fewer sources than sensors, sufficient snapshots, white spatial noise and a calibrated array. A ULA has front/back ambiguity outside the restricted field of view. Endfire sensitivity is poor; spacing greater than half a wavelength is disallowed to avoid grating-lobe ambiguity. Multiple coherent paths with different angles break the simple rank/subspace model; spatial smoothing or a wideband/coherent multipath estimator would be needed. This project does not implement those methods or range, velocity, radar cross section or delay-Doppler sensing.

## Monte Carlo interpretation

The checked-in suite uses 240 independent frames per Eb/N0 point and channel, 32 symbols per frame: 552,960 information bits at each QPSK point. Seven points span 0–30 dB. CSI MSE uses 80 independent frames per point; MUSIC uses 160 independent fading/noise trials per point with eight symbols each.

JSON records errors, bit counts, errored-frame counts and whole-frame bootstrap percentile intervals (1,000 resamples). Frame resampling preserves within-frame dependence from a shared fade. Estimates with few errored frames are unstable; bootstrap intervals do not establish unobserved rare-event rates. The sampled error count, not a smoothed extrapolation, defines BER.

Zero observed errors are shown as downward triangles at 1/Nbits, a plotting convention **not an estimate or confidence limit**. JSON includes 1-0.05^(1/Nbits) as a one-sided iid-bit upper limit, which is applicable only when bit errors are independent (e.g. the AWGN perfect-CSI QPSK case). Block fading and noisy shared pilots violate that independence. For zero-error fading points, 1-0.05^(1/Nframes) bounds the probability that an independent frame contains any error; because frame BER <= frame-error indicator, this is also a conservative BER upper bound. For 240 frames it is about 0.0124. More independent fades are needed before claiming very low fading BER. The off-grid sensing angle has a nearest-grid error of 0.03 degrees, which limits high-SNR RMSE.

## References

- [NumPy FFT documentation](https://numpy.org/doc/stable/reference/generated/numpy.fft.fft.html): transform normalization.
- [MathWorks MUSIC explanation](https://www.mathworks.com/help/phased/ug/music-super-resolution-doa-estimation.html): spatial covariance and noise-subspace direction finding.
- [MathWorks spatial smoothing](https://www.mathworks.com/help/phased/ref/spsmooth.html): the coherent-source limitation motivating the single-angle baseline.
