#!/usr/bin/env python3
"""
opto_calibration.py
═══════════════════
Doric LDFL5_450 (473 nm) laser calibration and optotagging protocol calculator.

Calibration is two-step:
    modulation (0-1)  →  Ia (mA)   [PCHIP on 3 measured mod points]
    Ia (mA)           →  mW        [PCHIP on 15-point dense Ia table]

Fit rationale — PCHIP (Piecewise Cubic Hermite Interpolating Polynomial)
    • Monotone between nodes — no spurious dips or overshoots
    • Exact at every measured node
    • C¹ continuous — smooth first derivative
    • Locally controlled — one uncertain point can't corrupt distant intervals
    Better than cubic spline (can overshoot) or polynomial (Runge oscillations).
    Ia→mW also has a linear physics fit (diode slope efficiency) for reference.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from scipy.interpolate import PchipInterpolator

# ═══════════════════════════════════════════════════════════════════════════════
# 1.  CALIBRATION TABLES
# ═══════════════════════════════════════════════════════════════════════════════

# ── Modulation → Ia  (3 directly measured operating points) ──────────────────
# Replace modulation values with your measured DAC voltages / 5 V when available
MOD_IA_TABLE: list[tuple[float, float]] = [
    # (modulation, Ia_mA)
    (0.25,   30),
    (0.50,   90),
    (1.00,  120),
]

# ── Ia → mW  (dense bench measurement at fiber tip, 470 nm bandpass) ─────────
# Ia = 18 mA is the confirmed lasing threshold (0 mW).
# Ia = 15 mA included to anchor the sub-threshold flat region.
# To suppress anchor effect on curvature: comment out the (18, 0.0) row and
# set IA_THRESHOLD_MA = 18.0 manually below.
IA_MW_TABLE: list[tuple[float, float]] = [
    # (Ia_mA, power_mW)
    (15,    0.0),   # below threshold — anchor for flat region
    # (18,  0.0),   # lasing threshold — uncomment if anchor effect observed
    (19,    0.6),
    (20,    1.1),
    (25,    4.4),
    (30,    8.0),
    (35,   10.7),
    (40,   14.3),
    (50,   20.1),
    (60,   26.7),
    (70,   33.0),
    (80,   39.0),
    (90,   45.0),
    (100,  51.0),
    (109,  56.1),
    (120,  62.0),   # confirmed fiber-tip max at mod=1.0 (diode ~90 mW, ~28 mW lost in coupling)
]

IA_THRESHOLD_MA  = 18.0    # confirmed lasing threshold
MOD_THRESHOLD    = 0.211   # inferred from quadratic fit to MOD_IA_TABLE
LASER_MAX_MW     = 62.0    # fiber-tip max at Ia=120 mA / mod=1.0
FIXED_OVERHEAD_S = 6.0     # start/shutdown fixed cost per condition (seconds)


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  LASER CALIBRATION CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class LaserCalibration:
    """
    Two-step PCHIP calibration for Doric LDFL5_450.

    Step 1  mod  → Ia   (PCHIP on MOD_IA_TABLE — 3 operating points)
    Step 2  Ia   → mW   (PCHIP on IA_MW_TABLE  — 14-point dense table)

    Primary interface
    -----------------
    calib.lookup(target_mw)        → dict(modulation, ia_mA, actual_mw)
    calib.print_table([mw, ...])   → formatted console table
    calib.plot()                   → calibration figures
    """

    def __init__(
        self,
        mod_ia_table: list = MOD_IA_TABLE,
        ia_mw_table:  list = IA_MW_TABLE,
        ia_threshold: float = IA_THRESHOLD_MA,
    ):
        self.ia_threshold = ia_threshold

        # ── Step 1: mod → Ia ──────────────────────────────────────────────────
        mi = np.array(sorted(mod_ia_table, key=lambda x: x[0]), dtype=float)
        self.mod_pts = mi[:, 0]
        self.ia_from_mod_pts = mi[:, 1]
        self._mod_to_ia = PchipInterpolator(self.mod_pts, self.ia_from_mod_pts,
                                            extrapolate=False)
        self._ia_to_mod = PchipInterpolator(self.ia_from_mod_pts, self.mod_pts,
                                            extrapolate=False)

        # ── Step 2: Ia → mW ───────────────────────────────────────────────────
        im = np.array(sorted(ia_mw_table, key=lambda x: x[0]), dtype=float)
        self.ia_pts = im[:, 0]
        self.mw_pts = im[:, 1]
        self._ia_to_mw = PchipInterpolator(self.ia_pts, self.mw_pts,
                                           extrapolate=False)
        # Inverse (monotone above threshold → valid)
        above = im[im[:, 1] > 0]
        self._mw_to_ia = PchipInterpolator(above[:, 1], above[:, 0],
                                           extrapolate=False)

        # ── Physics fit: mW = slope × (Ia − threshold) ────────────────────────
        above_thresh = im[im[:, 0] > ia_threshold]
        delta_ia = above_thresh[:, 0] - ia_threshold
        self.slope_eff = float(
            np.dot(delta_ia, above_thresh[:, 1]) / np.dot(delta_ia, delta_ia)
        )  # mW / mA, least-squares through origin

    # ── core lookups ──────────────────────────────────────────────────────────

    def ia_from_mod(self, mod: float) -> float:
        mod = float(np.clip(mod, self.mod_pts[0], self.mod_pts[-1]))
        return float(self._mod_to_ia(mod))

    def mw_from_ia(self, ia: float) -> float:
        ia = float(np.clip(ia, self.ia_pts[0], self.ia_pts[-1]))
        return float(self._ia_to_mw(ia))

    def mw_from_mod(self, mod: float) -> float:
        return self.mw_from_ia(self.ia_from_mod(mod))

    def ia_from_mw(self, target_mw: float) -> float:
        target_mw = float(np.clip(target_mw, self.mw_pts[self.mw_pts > 0].min(),
                                  self.mw_pts.max()))
        return float(self._mw_to_ia(target_mw))

    def mod_from_ia(self, ia: float) -> float:
        ia = float(np.clip(ia, self.ia_from_mod_pts[0], self.ia_from_mod_pts[-1]))
        return float(self._ia_to_mod(ia))

    def mod_from_mw(self, target_mw: float) -> float:
        return self.mod_from_ia(self.ia_from_mw(target_mw))

    def lookup(self, target_mw: float) -> dict:
        """target mW → modulation (0-1), Ia (mA), actual mW"""
        ia     = self.ia_from_mw(target_mw)
        mod    = self.mod_from_ia(ia)
        actual = self.mw_from_ia(ia)
        return dict(
            target_mw  = target_mw,
            modulation = round(mod,    4),
            ia_mA      = round(ia,     1),
            actual_mw  = round(actual, 2),
        )

    def print_table(self, target_powers_mw: list[float]):
        print(f"\n{'Target mW':>10}  {'Modulation':>10}  {'Ia (mA)':>8}  {'Actual mW':>10}")
        print("─" * 46)
        for p in target_powers_mw:
            r = self.lookup(p)
            print(f"{r['target_mw']:>10.1f}  {r['modulation']:>10.4f}  "
                  f"{r['ia_mA']:>8.1f}  {r['actual_mw']:>10.2f}")

    def plot(self, ax=None, save_path=None):
        """
        Single publication-quality calibration panel.
        Primary x-axis: Ia (mA). Secondary x-axis (top): Modulation (0-1),
        ticked only at the 3 confirmed operating points.
        """
        _mod_confirmed = np.array([0.25,  0.50,  1.00])
        _ia_confirmed  = np.array([30.,   90.,  120.])
        _ia_to_mod_spl = PchipInterpolator(_ia_confirmed, _mod_confirmed, extrapolate=True)
        _mod_to_ia_spl = PchipInterpolator(_mod_confirmed, _ia_confirmed, extrapolate=True)

        if ax is None:
            fig, ax = plt.subplots(figsize=(6.0, 4.2))
        else:
            fig = ax.get_figure()

        ia_fine  = np.linspace(self.ia_pts[0], self.ia_pts[-1], 600)
        mw_pchip = np.array([self.mw_from_ia(x) for x in ia_fine])
        mw_lin   = np.maximum(0., self.slope_eff * (ia_fine - self.ia_threshold))

        ax.plot(ia_fine, mw_pchip, color="#1b6ca8", lw=2.2, zorder=3, label="PCHIP fit")
        ax.plot(ia_fine, mw_lin,   color="#3a9e3a", lw=1.4, ls="--", zorder=2,
                label=f"Linear  η = {self.slope_eff:.3f} mW mA⁻¹")
        ax.scatter(self.ia_pts, self.mw_pts, s=52, color="#c0392b",
                   zorder=5, label="Measured", clip_on=False)

        mw_confirmed = np.array([self.mw_from_ia(ia) for ia in _ia_confirmed])
        ax.scatter(_ia_confirmed, mw_confirmed, s=100, marker="D",
                   color="#c0392b", edgecolors="white", linewidths=0.8,
                   zorder=6, label="Mod-confirmed (×3)")

        ax.axvline(self.ia_threshold, color="#999999", ls=":", lw=1.1, zorder=1)
        ax.text(self.ia_threshold + 0.8, 1.5,
                f"threshold\n{self.ia_threshold:.0f} mA",
                fontsize=7.5, color="#777777", va="bottom", ha="left")

        ax.set_xlabel("Driver current  $I_a$  (mA)", fontsize=10, labelpad=6)
        ax.set_ylabel("Output power  (mW)",           fontsize=10, labelpad=6)
        ax.set_xlim(self.ia_pts[0] - 2, self.ia_pts[-1] + 3)
        ax.set_ylim(-1, self.mw_pts[-1] * 1.06)

        def _fwd(x):
            return _ia_to_mod_spl(np.clip(np.asarray(x, float),
                                          _ia_confirmed[0], _ia_confirmed[-1]))
        def _inv(m):
            return _mod_to_ia_spl(np.clip(np.asarray(m, float),
                                          _mod_confirmed[0], _mod_confirmed[-1]))

        secax = ax.secondary_xaxis("top", functions=(_fwd, _inv))
        secax.set_xticks(_mod_confirmed)
        secax.set_xticklabels(["0.25", "0.50", "1.00"])
        secax.set_xlabel("Modulation  (0–1)", fontsize=10, labelpad=7)
        secax.tick_params(axis="x", direction="out", length=4, labelsize=8.5, pad=3)

        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.tick_params(axis="both", direction="out", length=4,
                       labelsize=8.5, top=False, right=False)
        ax.yaxis.set_tick_params(pad=3)
        ax.grid(axis="y", color="#dddddd", lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, fontsize=8.5, loc="upper left",
                  handlelength=1.8, labelspacing=0.4)

        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
        return fig, ax

    def _old_three_panel(self):
        """(kept for reference — replaced by single-panel plot())"""
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        fig.suptitle("Doric LDFL5_450  Calibration  (473 nm)", fontsize=13)

        # ── Panel 1: Ia → mW (dense data + linear fit) ────────────────────────
        ax = axes[0]
        ia_fine  = np.linspace(self.ia_pts[0], self.ia_pts[-1], 500)
        mw_fine  = np.array([self.mw_from_ia(x) for x in ia_fine])
        mw_lin   = np.maximum(0, self.slope_eff * (ia_fine - self.ia_threshold))

        ax.plot(ia_fine, mw_fine,  color="steelblue", lw=2.5, label="PCHIP fit")
        ax.plot(ia_fine, mw_lin,   color="green",     lw=1.5,
                ls="--", label=f"Linear (η = {self.slope_eff:.3f} mW/mA)")
        ax.scatter(self.ia_pts, self.mw_pts, c="crimson", s=60, zorder=5,
                   label="Measured")
        ax.axvline(self.ia_threshold, color="gray", ls=":", lw=1.2,
                   label=f"Threshold ({self.ia_threshold:.0f} mA)")
        ax.set_xlabel("Driver Current Ia (mA)", fontsize=11)
        ax.set_ylabel("Power (mW)", fontsize=11)
        ax.set_title("Ia → mW  (dense bench calibration)")
        ax.legend(fontsize=8.5); ax.grid(True, alpha=0.3)

        # ── Panel 2: mod → Ia ─────────────────────────────────────────────────
        ax = axes[1]
        mod_fine = np.linspace(self.mod_pts[0], self.mod_pts[-1], 300)
        ia_interp = np.array([self.ia_from_mod(m) for m in mod_fine])

        ax.plot(mod_fine, ia_interp, color="darkorange", lw=2.5, label="PCHIP fit")
        ax.scatter(self.mod_pts, self.ia_from_mod_pts, c="crimson", s=80,
                   zorder=5, label="Measured")
        for m, ia in zip(self.mod_pts, self.ia_from_mod_pts):
            ax.annotate(f"{ia:.0f} mA", (m, ia),
                        textcoords="offset points", xytext=(5, 4), fontsize=8)
        ax.set_xlabel("Modulation (0–1)", fontsize=11)
        ax.set_ylabel("Driver Current Ia (mA)", fontsize=11)
        ax.set_title("Modulation → Ia\n(3 measured operating points)")
        ax.legend(fontsize=8.5); ax.grid(True, alpha=0.3)

        # ── Panel 3: mod → mW (two-step, end-to-end) ─────────────────────────
        ax = axes[2]
        mw_end  = np.array([self.mw_from_mod(m) for m in mod_fine])

        ax.plot(mod_fine, mw_end, color="purple", lw=2.5, label="PCHIP (two-step)")
        # Overlay measured mod points
        mw_at_mod = [self.mw_from_ia(ia) for ia in self.ia_from_mod_pts]
        ax.scatter(self.mod_pts, mw_at_mod, c="crimson", s=80, zorder=5,
                   label="Measured mod points")
        for m, mw in zip(self.mod_pts, mw_at_mod):
            ax.annotate(f"{mw:.1f} mW", (m, mw),
                        textcoords="offset points", xytext=(5, 4), fontsize=8)
        ax.set_xlabel("Modulation (0–1)", fontsize=11)
        ax.set_ylabel("Power (mW)", fontsize=11)
        ax.set_title("Modulation → mW  (end-to-end)\n(two-step via Ia)")
        ax.legend(fontsize=8.5); ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  COLLISION YIELD CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

def collision_yield(
    stim_rate_hz:       float,
    spont_rate_hz:      float,
    latency_ms:         float,
    refractory_ms:      float = 0.8,
    blanking_before_ms: float = 0.15,
    duration_min:       float = 3.0,
) -> dict:
    """
    Expected antidromic collision events.

    Accessible collision window = latency − refractory − blanking_before
    Expected events = stim_rate × duration_s × spont_rate × (window_s)
    """
    w_total = max(0.0, latency_ms - refractory_ms)
    w_acc   = max(0.0, w_total - blanking_before_ms)
    dur_s   = duration_min * 60.0

    ev_per_min = stim_rate_hz * 60.0 * spont_rate_hz * (w_acc / 1000.0)
    ev_total   = ev_per_min * duration_min

    def mins_for(n):
        return (n / ev_per_min) if ev_per_min > 0 else np.inf

    return dict(
        stim_rate_hz         = stim_rate_hz,
        spont_rate_hz        = spont_rate_hz,
        latency_ms           = latency_ms,
        refractory_ms        = refractory_ms,
        collision_window_ms  = w_total,
        accessible_window_ms = w_acc,
        blanking_before_ms   = blanking_before_ms,
        events_per_min       = ev_per_min,
        total_events         = ev_total,
        total_pulses         = stim_rate_hz * dur_s,
        duration_min         = duration_min,
        mins_for_10          = mins_for(10),
        mins_for_20          = mins_for(20),
        feasible             = w_acc > 0 and ev_per_min > 0,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  PROTOCOL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _cond_time_s(n_pulses: int, rate_hz: float) -> float:
    return FIXED_OVERHEAD_S + n_pulses / rate_hz


def somatic_protocol(calib: LaserCalibration) -> dict:
    """
    Somatic optotagging protocol.

    Power ramp  : 10 Hz | 5 ms | log-spaced 1–56 mW | pulse count tapered
                  to cap energy ≤ 12 mJ per level
    Following   : 40 Hz and 60 Hz | 1 ms | 10 trains × 20 pulses | 3 s ITI
                  fixed 10 mW (suprathreshold)
    """
    ramp_mw   = [1, 2, 5, 10, 20, 40, 56]
    ramp_rate = 10
    pulse_ms  = 5.0

    def n_pulses(p_mw, cap_mj=12.0):
        return max(20, min(int(cap_mj / (p_mw * pulse_ms / 1000)), 200))

    ramp_table = []
    for p in ramp_mw:
        n   = n_pulses(p)
        e   = p * n * pulse_ms / 1e3
        t   = _cond_time_s(n, ramp_rate)
        r   = calib.lookup(p)
        ramp_table.append(dict(n_pulses=n, energy_mj=round(e,1),
                               time_s=round(t,1), **r))

    ramp_total_s = sum(r["time_s"] for r in ramp_table)

    follow_table = []
    for fhz in [40, 60]:
        n_trains, ppt, iti = 10, 20, 3.0
        train_s  = ppt / fhz
        total_s  = FIXED_OVERHEAD_S + n_trains * (train_s + iti)
        follow_table.append(dict(
            freq_hz=fhz, pulse_ms=1.0, n_trains=n_trains,
            pulses_p_train=ppt, total_pulses=n_trains*ppt,
            train_s=round(train_s,2), iti_s=iti,
            total_s=round(total_s,1),
            duty_pct=round(1.0/1000*fhz*100,1),
            power_mw=10.0,
        ))

    follow_total_s = sum(r["total_s"] for r in follow_table)
    return dict(ramp=ramp_table, ramp_total_s=ramp_total_s,
                following=follow_table, follow_total_s=follow_total_s,
                grand_total_s=ramp_total_s+follow_total_s)


def antidromic_protocol() -> dict:
    """
    Antidromic protocol: 80 mW, 3 ms and 5 ms, 20 Hz.
    Primary (5 ms) runs longer for collision accumulation.
    """
    # (pulse_ms, power_mw, duration_min, note)
    _conditions: list[tuple[float, float, float, str]] = [
        (5.0, 80.0, 3.0, "primary — collision + reliability"),
        (3.0, 80.0, 2.0, "crosscheck — artefact-shifted"),
    ]
    rate_hz = 20.0
    results = []
    for pul_ms, pwr_mw, dur_min, note in _conditions:
        n      = int(rate_hz * dur_min * 60)
        duty   = pul_ms / 1000 * rate_hz
        total  = FIXED_OVERHEAD_S + dur_min * 60
        energy = pwr_mw * (pul_ms / 1000) * n
        results.append(dict(pulse_ms=pul_ms, power_mw=pwr_mw,
                            duration_min=dur_min, note=note,
                            rate_hz=rate_hz, n_pulses=n,
                            duty_pct=round(duty * 100, 1),
                            total_s=round(total, 1),
                            energy_mj=round(energy, 0)))
    return dict(conditions=results,
                grand_total_s=sum(r["total_s"] for r in results))


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  COLLISION ANALYSIS PLOT
# ═══════════════════════════════════════════════════════════════════════════════

def plot_collision_analysis(
    latency_ms:         float = 1.26,
    refractory_ms:      float = 0.8,
    blanking_before_ms: float = 0.15,
    stim_rates:         list  = [10, 20, 40],
    spont_rates:        list  = [2, 5, 10, 20],
    duration_range_min: tuple = (0.5, 10.0),
    pulse_duration_ms:  float = 5.0,
):
    w_acc  = max(0, latency_ms - refractory_ms - blanking_before_ms)
    title  = (f"Collision Yield  |  latency {latency_ms} ms  "
              f"refractory {refractory_ms} ms  blanking {blanking_before_ms} ms"
              f"  →  accessible window = {w_acc:.2f} ms")

    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(title, fontsize=11)
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.35)
    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1])
    axC = fig.add_subplot(gs[1, 0])
    axD = fig.add_subplot(gs[1, 1])

    durations  = np.linspace(*duration_range_min, 300)
    cmap       = plt.cm.viridis
    spont_norm = Normalize(vmin=0, vmax=len(spont_rates)-1)
    lstyles    = ["-", "--", "-.", ":"]

    # A: events vs duration
    for i, r in enumerate(spont_rates):
        col = cmap(spont_norm(i))
        for j, sr in enumerate(stim_rates):
            y   = collision_yield(sr, r, latency_ms, refractory_ms,
                                  blanking_before_ms, 1.0)
            axA.plot(durations, y["events_per_min"]*durations,
                     color=col, ls=lstyles[j%4], lw=1.8,
                     label=f"r={r} Hz, {sr} Hz")
    axA.axhline(20, color="crimson",    ls=":", lw=1.2, label="n=20")
    axA.axhline(10, color="darkorange", ls=":", lw=1.2, label="n=10")
    axA.set_xlabel("Duration (min)"); axA.set_ylabel("Expected collision events")
    axA.set_title("A  Events vs duration")
    axA.legend(fontsize=6, ncol=2); axA.grid(True, alpha=0.25); axA.set_ylim(bottom=0)

    # B: time to 20 events vs spontaneous rate
    r_range = np.linspace(0.5, 30, 400)
    for j, sr in enumerate(stim_rates):
        t20 = []
        for r in r_range:
            y = collision_yield(sr, r, latency_ms, refractory_ms, blanking_before_ms, 1.0)
            t20.append(min(20/y["events_per_min"] if y["events_per_min"]>0 else 60, 60))
        axB.plot(r_range, t20, ls=lstyles[j%4], lw=2.0, label=f"{sr} Hz stim")
    axB.axhline(5,  color="green",      ls=":", lw=1.2, label="5 min")
    axB.axhline(10, color="darkorange", ls=":", lw=1.2, label="10 min")
    axB.set_xlabel("Spontaneous rate (Hz)"); axB.set_ylabel("Min to 20 collisions")
    axB.set_title("B  Time to 20 events vs firing rate")
    axB.legend(fontsize=9); axB.grid(True, alpha=0.25); axB.set_ylim(0, 35)

    # C: total pulses vs duration
    for j, sr in enumerate(stim_rates):
        duty = sr * pulse_duration_ms / 1000
        axC.plot(durations, sr*60*durations, ls=lstyles[j%4], lw=2.0,
                 label=f"{sr} Hz  (duty {duty*100:.0f}%)")
    for n, col, lbl in [(200,"steelblue","200"), (1000,"darkorange","1 000"), (3600,"crimson","3 600")]:
        axC.axhline(n, color=col, ls=":", lw=1.0, label=f"{lbl} pulses")
    axC.set_xlabel("Duration (min)"); axC.set_ylabel("Total pulses")
    axC.set_title(f"C  Total pulses ({pulse_duration_ms:.0f} ms pulses)")
    axC.legend(fontsize=9); axC.grid(True, alpha=0.25)

    # D: summary table
    axD.axis("off")
    col_labels = ["r_spont"] + [f"{sr} Hz" for sr in stim_rates]
    rows = []
    for r in spont_rates:
        row = [f"{r} Hz"]
        for sr in stim_rates:
            y = collision_yield(sr, r, latency_ms, refractory_ms, blanking_before_ms, 3.0)
            n = y["total_events"]
            row.append(f"{n:.1f}  {'✓' if n>=10 else ('~' if n>=5 else '✗')}")
        rows.append(row)
    tbl = axD.table(cellText=rows, colLabels=col_labels, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9.5); tbl.scale(1.1, 2.2)
    for (ri, ci), cell in tbl.get_celld().items():
        if ri == 0: cell.set_facecolor("#d0d0d0"); continue
        t = cell.get_text().get_text()
        cell.set_facecolor("#c8e6c9" if "✓" in t else "#fff9c4" if "~" in t else "#ffcdd2")
    axD.set_title("D  Collision events in 3 min\n✓ ≥10  ~  5–9  ✗ <5", fontsize=10)

    sm = ScalarMappable(cmap=cmap, norm=spont_norm)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=[axA,axB], orientation="vertical",
                      fraction=0.015, pad=0.04, shrink=0.6)
    cb.set_ticks(range(len(spont_rates)))
    cb.set_ticklabels([f"{r} Hz" for r in spont_rates])
    cb.set_label("Spontaneous rate", fontsize=9)
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  __main__
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse, pathlib

    parser = argparse.ArgumentParser(description="Doric LDFL5_450 calibration + protocol summary")
    parser.add_argument("--save-dir", type=pathlib.Path, default=None,
                        help="Directory to save figures (default: show only)")
    args = parser.parse_args()

    calib = LaserCalibration()

    print("\n" + "═"*60)
    print("LASER CALIBRATION  —  Doric LDFL5_450 (473 nm)")
    print("═"*60)
    print(f"  Slope efficiency : {calib.slope_eff:.3f} mW/mA  (above {IA_THRESHOLD_MA:.0f} mA threshold)")
    print(f"  Max output       : {calib.mw_pts.max():.1f} mW  at Ia = {calib.ia_pts.max():.0f} mA")

    print("\n  Full Ia → mW table (PCHIP interpolated at round targets):")
    calib.print_table([1, 2, 5, 10, 15, 20, 30, 40, 56])

    print("\n" + "═"*60)
    print("SOMATIC PROTOCOL")
    print("═"*60)
    som = somatic_protocol(calib)
    print(f"\n  {'mW':>5}  {'mod':>8}  {'Ia(mA)':>7}  {'pulses':>7}  {'mJ':>6}  {'s':>6}")
    print("  " + "─"*46)
    for r in som["ramp"]:
        print(f"  {r['target_mw']:>5.0f}  {r['modulation']:>8.4f}  {r['ia_mA']:>7.1f}"
              f"  {r['n_pulses']:>7}  {r['energy_mj']:>6.1f}  {r['time_s']:>6.1f}")
    print(f"\n  Ramp total    : {som['ramp_total_s']:.0f} s  ({som['ramp_total_s']/60:.1f} min)")
    for f in som["following"]:
        print(f"  Following {f['freq_hz']:>2}Hz : {f['total_pulses']} pulses | "
              f"duty {f['duty_pct']:.0f}% | {f['total_s']:.0f} s")
    print(f"  Somatic total : {som['grand_total_s']:.0f} s  ({som['grand_total_s']/60:.1f} min)")

    print("\n" + "═"*60)
    print("ANTIDROMIC PROTOCOL")
    print("═"*60)
    anti = antidromic_protocol()
    print(f"\n  {'ms':>4}  {'mW':>5}  {'Hz':>4}  {'pulses':>7}  {'duty%':>6}  "
          f"{'mJ':>7}  {'s':>6}  note")
    print("  " + "─"*68)
    for c in anti["conditions"]:
        print(f"  {c['pulse_ms']:>4.0f}  {c['power_mw']:>5.0f}  {c['rate_hz']:>4.0f}  "
              f"{c['n_pulses']:>7}  {c['duty_pct']:>6.1f}  {c['energy_mj']:>7.0f}  "
              f"{c['total_s']:>6.1f}  {c['note']}")

    total_s = som["grand_total_s"] + anti["grand_total_s"]
    print(f"\n  {'─'*40}")
    print(f"  TOTAL OPTOTAGGING : {total_s:.0f} s  ({total_s/60:.1f} min)")

    save_cal = (args.save_dir / "calibration_curves.png") if args.save_dir else None
    save_col = (args.save_dir / "collision_analysis.png") if args.save_dir else None

    calib.plot(save_path=save_cal)
    plt.close("all")

    plot_collision_analysis(
        latency_ms=1.26, refractory_ms=0.8, blanking_before_ms=0.15,
        stim_rates=[10, 20, 40], spont_rates=[2, 5, 10, 20], pulse_duration_ms=5.0,
    )
    if save_col:
        plt.savefig(save_col, dpi=150, bbox_inches="tight")

    plt.show()
    print("\nDone.")
