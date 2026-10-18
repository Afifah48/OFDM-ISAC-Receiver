"""Run with `ofdm-isac --config configs/baseline.yaml --output results`."""
import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import platform
import tempfile
import time

# Keep Matplotlib's cache out of the user's home and the tracked repository.
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ofdm-isac-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import erfc

from ofdm_isac.channel.models import Observation, propagate
from ofdm_isac.receiver.processing import receive
from ofdm_isac.sensing.music import music
from ofdm_isac.transmitter.ofdm import transmit
from ofdm_isac.utils.config import Config, load_config


def error_summary(errors, bits_per_frame):
    errors = np.asarray(errors)
    count = int(errors.sum())
    total = int(len(errors) * bits_per_frame)
    # Whole-frame bootstrap respects within-frame block-fading dependence.
    rng = np.random.default_rng(4800)
    bootstrap = rng.choice(errors, size=(1000, len(errors))).mean(axis=1) / bits_per_frame
    return {"errors": count, "bits": total, "frames": len(errors), "ber": count / total,
            "errored_frames": int(np.count_nonzero(errors)),
            "frame_bootstrap_95": np.quantile(bootstrap, [0.025, 0.975]).tolist(),
            "zero_error_iid_bit_upper_95": float(-np.expm1(np.log(0.05) / total)) if count == 0 else None,
            "zero_error_frame_event_upper_95": float(-np.expm1(np.log(0.05) / len(errors))) if count == 0 else None}


def communication(config, levels, frames, rng):
    records = []
    for level in levels:
        errors = {name: [] for name in ("siso_ls", "siso_perfect", "simo_ls", "simo_perfect")}
        for _ in range(frames):
            tx = transmit(config, rng)
            obs = propagate(tx.waveform, config, rng, ebn0_db=float(level))
            first = Observation(obs.waveform[:1], obs.response[:1], obs.taps[:1], obs.noise_variance)
            for prefix, observation, cfg in (("simo", obs, config), ("siso", first, replace(config, n_rx=1))):
                for perfect in (False, True):
                    rx = receive(observation, cfg, perfect_csi=perfect)
                    name = prefix + ("_perfect" if perfect else "_ls")
                    errors[name].append(np.count_nonzero(rx.bits != tx.bits))
        records.append({"ebn0_db": float(level), **{name: error_summary(err, tx.bits.size) for name, err in errors.items()}})
        print(f"{config.channel} Eb/N0={level:g}: SISO LS={records[-1]['siso_ls']['ber']:.4g}, SIMO LS={records[-1]['simo_ls']['ber']:.4g}", flush=True)
    return records


def channel_mse(config, levels, frames, rng):
    result = []
    indices = config.data_signed % config.n_fft
    for level in levels:
        mse = []
        for _ in range(frames):
            tx = transmit(config, rng)
            obs = propagate(tx.waveform, config, rng, snr_db=float(level))
            rx = receive(obs, config)
            mse.append(np.mean(abs(rx.csi[:, :, indices] - obs.response[:, None, indices])**2))
        result.append({"snr_db": float(level), "mse": float(np.mean(mse)), "frames": frames})
    return result


def sensing(config, levels, trials, rng):
    config = replace(config, channel="spatial", angle_deg=23.37, n_symbols=8)
    records = []
    example = None
    for level in levels:
        estimates, errors = [], []
        for _ in range(trials):
            tx = transmit(config, rng)
            obs = propagate(tx.waveform, config, rng, snr_db=float(level))
            rx = receive(obs, config)
            # Same FFT observations used by the communications receiver; guards/DC excluded.
            snapshots = rx.grid[:, :, config.active_signed % config.n_fft].reshape(config.n_rx, -1)
            result = music(snapshots, config.spacing_wavelengths)
            estimates.append(result.angle_deg)
            errors.append(np.count_nonzero(rx.bits != tx.bits))
            example = (result, config.angle_deg, rx.grid.copy(), obs.waveform.copy())
        delta = np.asarray(estimates) - config.angle_deg
        records.append({"snr_db": float(level), "true_angle_deg": config.angle_deg,
                        "rmse_deg": float(np.sqrt(np.mean(delta**2))),
                        "bias_deg": float(np.mean(delta)), "trials": trials,
                        "estimates_deg": estimates,
                        "communication": error_summary(errors, tx.bits.size)})
        print(f"MUSIC SNR={level:g}: RMSE={records[-1]['rmse_deg']:.4g} deg", flush=True)
    return records, example


def save_plot(path, title, xlabel, ylabel):
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, which="both", alpha=0.25)
    handles, _ = plt.gca().get_legend_handles_labels()
    if handles:
        plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def plot_ber(records, key, label):
    x = np.array([r["ebn0_db"] for r in records])
    y = np.array([r[key]["ber"] for r in records])
    # Zero counts are censored, not silently drawn as BER=0 on a log axis.
    plt.semilogy(x, np.where(y > 0, y, np.nan), "o-", label=label)
    for level, value, record in zip(x, y, records):
        if value == 0:
            plt.semilogy(level, 1 / record[key]["bits"], "v", color=plt.gca().lines[-1].get_color())


def run(config, output, frames=240, trials=160, step=5):
    if frames < 2 or trials < 2 or step < 1 or config.n_rx < 2:
        raise ValueError("Suite requires >=2 frames/trials/antennas and positive SNR step")
    if config.cfo or config.timing_offset:
        raise ValueError("Suite assumes zero CFO/timing offset; use impairment script for offsets")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    levels = np.unique(np.r_[np.arange(0, 31, step), 30])
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(config.seed).spawn(8)]
    start = time.perf_counter()
    baseline = communication(config, levels, frames, streams[0])
    mse = channel_mse(config, levels, max(40, frames // 3), streams[1])
    aoa, example = sensing(config, levels, trials, streams[2])
    scenarios = {}
    for i, (name, cfg) in enumerate([
        ("awgn", replace(config, channel="awgn")),
        ("flat_rayleigh", replace(config, channel="rayleigh", tap_delays=(0,), tap_powers_db=(0,))),
        ("long_delay", replace(config, channel="rayleigh", tap_delays=(0, 6, 12), tap_powers_db=(0, -4, -8)))
    ]):
        if max(cfg.tap_delays) > cfg.cp:
            raise ValueError("Long-delay experiment requires CP>=12")
        scenarios[name] = communication(cfg, levels, frames, streams[i + 3])
    summary = {"config": asdict(config), "frames_per_point": frames, "aoa_trials_per_point": trials,
               "numpy_version": np.__version__, "python_version": platform.python_version(),
               "baseline": baseline, "channel_mse": mse, "sensing": aoa, "scenarios": scenarios,
               "elapsed_seconds": time.perf_counter() - start}
    (output / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for key, label in [("siso_ls", "1x1 pilot LS"), ("simo_ls", f"1x{config.n_rx} pilot LS"),
                       ("siso_perfect", "1x1 perfect CSI"), ("simo_perfect", f"1x{config.n_rx} perfect CSI")]:
        plot_ber(baseline, key, label)
    save_plot(output / "ber.png", "Block Rayleigh OFDM: combining and CSI", "Transmitter Eb/N0 (dB)", "Bit error rate (v: zero errors, plotted at 1/Nbits)")
    for name, records in {"baseline_multipath": baseline, **scenarios}.items():
        plot_ber(records, "simo_ls", name)
    save_plot(output / "channels.png", "Channel sensitivity: pilot-LS SIMO", "Transmitter Eb/N0 (dB)", "Bit error rate (v: zero observed errors)")
    awgn = scenarios["awgn"]
    plot_ber(awgn, "siso_perfect", "AWGN SISO perfect CSI")
    plot_ber(awgn, "simo_perfect", f"AWGN 1x{config.n_rx} perfect CSI")
    if config.modulation == "QPSK":
        for gain, label in [(1, "SISO theory incl. overhead"), (config.n_rx, "SIMO theory incl. array gain")]:
            theory = 0.5 * erfc(np.sqrt(gain * 10.0**(levels / 10) / (2 * config.eb_tx)))
            plt.semilogy(levels, np.maximum(theory, 1e-12), "--", label=label)
    plt.ylim(1e-7, 0.3)
    save_plot(output / "awgn.png", "AWGN normalization check", "Transmitter Eb/N0 (dB)", "Bit error rate (v: zero observed errors)")
    plt.semilogy([r["snr_db"] for r in mse], [r["mse"] for r in mse], "o-", label="Data-subcarrier CSI MSE")
    save_plot(output / "channel_mse.png", "Pilot LS and linear interpolation", "Unit-gain sample SNR (dB)", "Mean |H estimate - H| squared")
    plt.semilogy(levels, [r["rmse_deg"] for r in aoa], "o-", label=f"{trials} independent fading/noise trials")
    plt.axhline(0.03, ls="--", color="gray", label="Nearest-grid error for 23.37 deg")
    save_plot(output / "aoa_rmse.png", "Shared-waveform MUSIC accuracy (0.1 deg scan)", "Unit-gain sample SNR (dB)", "Angle RMSE (degrees)")
    result, truth, sensing_grid, sensing_waveform = example
    plt.plot(result.angles, result.spectrum_db, label="Normalized MUSIC pseudo-spectrum")
    plt.axvline(truth, color="black", ls="--", label=f"Actual {truth:.2f} deg")
    plt.axvline(result.angle_deg, color="tab:red", ls=":", label=f"Estimated {result.angle_deg:.1f} deg")
    save_plot(output / "music.png", "MUSIC on the communication array data at 30 dB SNR", "Broadside angle (degrees)", "Normalized pseudo-spectrum (dB)")
    tx = transmit(config, streams[6])
    obs = propagate(tx.waveform, config, streams[6], ebn0_db=15)
    rx = receive(obs, config)
    raw = rx.grid[0, :, config.data_signed % config.n_fft].reshape(-1)
    np.savez_compressed(output / "example_arrays.npz", transmitted_grid=tx.grid, taps=obs.taps,
                        received_waveform=obs.waveform, received_grid=rx.grid, estimated_csi=rx.csi,
                        equalized=rx.symbols, music_angles=result.angles, music_db=result.spectrum_db,
                        sensing_received_grid=sensing_grid, sensing_received_waveform=sensing_waveform)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, values, title in zip(axes, [raw, rx.symbols.reshape(-1)], ["Antenna 0 before equalization", "After pilot LS + MRC"]):
        ax.scatter(values.real, values.imag, s=5, alpha=0.4)
        ax.set(title=title, xlabel="In-phase", ylabel="Quadrature", aspect="equal")
        ax.grid(alpha=0.25)
    fig.suptitle(f"{config.modulation}, multipath, transmitter Eb/N0 = 15 dB")
    fig.tight_layout()
    fig.savefig(output / "constellation.png", dpi=160)
    plt.close(fig)
    print(f"Saved measured results to {output}; elapsed {summary['elapsed_seconds']:.1f}s", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--frames", type=int, default=240)
    parser.add_argument("--trials", type=int, default=160)
    parser.add_argument("--step", type=int, default=5)
    args = parser.parse_args()
    run(load_config(args.config) if args.config else Config(), args.output, args.frames, args.trials, args.step)


if __name__ == "__main__":
    main()
