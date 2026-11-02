"""Compare operator portfolio size with median mapped facility footprint.

Run from any directory:
    uv run --with matplotlib python plot_operator_scale_vs_facility_size.py
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.ticker import FuncFormatter


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
DEFAULT_INPUT = PROJECT_DIR / "clean_data_centers.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "operator_scale_vs_facility_size.png"

FOOTPRINT_CMAP = LinearSegmentedColormap.from_list(
    "footprint_orange", ["#FDE0B6", "#E69F00", "#D55E00"]
)

LABEL_OFFSETS = {
    "Amazon Web Services": (-8, -16),
    "Digital Realty": (-8, 12),
    "Equinix": (10, -13),
    "Microsoft": (10, 8),
    "Google": (10, 10),
    "Meta": (10, 10),
    "NTT": (-10, -14),
    "Quality Technology Services": (-10, 11),
    "CyrusOne": (10, -9),
    "Vantage Data Centers": (-10, 11),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare operator facility count with median facility footprint."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--minimum-footprints",
        type=int,
        default=5,
        help="Minimum number of usable footprint records required per operator.",
    )
    parser.add_argument(
        "--annotate",
        type=int,
        default=10,
        help="Number of operators with the largest total footprint to label.",
    )
    parser.add_argument("--show", action="store_true", help="Also open the chart window.")
    return parser.parse_args()


def load_operator_rows(
    csv_path: Path, minimum_footprints: int
) -> tuple[list[dict[str, object]], int, int]:
    if minimum_footprints < 1:
        raise ValueError("--minimum-footprints must be at least 1.")

    operators: dict[str, dict[str, object]] = defaultdict(
        lambda: {"facility_count": 0, "footprints": []}
    )
    unnamed_rows = 0
    missing_footprints = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"operator", "footprint_area_m2"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "The input CSV must contain operator and footprint_area_m2."
            )

        for record in reader:
            operator = record["operator"].strip()
            if not operator:
                unnamed_rows += 1
                continue

            operators[operator]["facility_count"] = (
                int(operators[operator]["facility_count"]) + 1
            )
            try:
                footprint = float(record["footprint_area_m2"])
            except (TypeError, ValueError):
                missing_footprints += 1
                continue

            if not math.isfinite(footprint) or footprint <= 0:
                missing_footprints += 1
                continue
            footprints = operators[operator]["footprints"]
            assert isinstance(footprints, list)
            footprints.append(footprint)

    rows: list[dict[str, object]] = []
    for operator, values in operators.items():
        footprints = values["footprints"]
        assert isinstance(footprints, list)
        if len(footprints) < minimum_footprints:
            continue
        rows.append(
            {
                "operator": operator,
                "facility_count": int(values["facility_count"]),
                "usable_footprints": len(footprints),
                "median_footprint": statistics.median(footprints),
                "total_footprint": sum(footprints),
            }
        )

    if len(rows) < 2:
        raise ValueError(
            "At least two operators must meet the minimum footprint threshold."
        )
    return rows, unnamed_rows, missing_footprints


def log_correlation_and_line(
    rows: list[dict[str, object]],
) -> tuple[float, float, float]:
    x = [math.log10(float(row["facility_count"])) for row in rows]
    y = [math.log10(float(row["median_footprint"])) for row in rows]
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    sum_xy = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    sum_xx = sum((a - mean_x) ** 2 for a in x)
    sum_yy = sum((b - mean_y) ** 2 for b in y)

    correlation = sum_xy / math.sqrt(sum_xx * sum_yy)
    slope = sum_xy / sum_xx
    intercept = mean_y - slope * mean_x
    return correlation, slope, intercept


def configure_typography() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 11,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "text.color": "#222222",
            "axes.labelcolor": "#222222",
            "xtick.color": "#444444",
            "ytick.color": "#444444",
        }
    )


def comma_tick(value: float, _position: int) -> str:
    return f"{value:,.0f}"


def abbreviated_tick(value: float, _position: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    if value >= 1_000:
        return f"{value / 1_000:g}k"
    return f"{value:g}"


def make_plot(
    rows: list[dict[str, object]],
    unnamed_rows: int,
    missing_footprints: int,
    minimum_footprints: int,
    output_path: Path,
    annotations: int,
    show: bool,
) -> None:
    correlation, slope, intercept = log_correlation_and_line(rows)
    configure_typography()
    fig, ax = plt.subplots(figsize=(11.5, 7.5))

    totals = [float(row["total_footprint"]) for row in rows]
    color_norm = LogNorm(vmin=min(totals), vmax=max(totals))
    scatter = ax.scatter(
        [float(row["facility_count"]) for row in rows],
        [float(row["median_footprint"]) for row in rows],
        c=totals,
        cmap=FOOTPRINT_CMAP,
        norm=color_norm,
        s=76,
        alpha=0.88,
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
    )

    min_x = min(float(row["facility_count"]) for row in rows)
    max_x = max(float(row["facility_count"]) for row in rows)
    line_log_x = [
        math.log10(min_x) + (math.log10(max_x) - math.log10(min_x)) * i / 200
        for i in range(201)
    ]
    line_x = [10**value for value in line_log_x]
    line_y = [10 ** (intercept + slope * value) for value in line_log_x]
    ax.plot(
        line_x,
        line_y,
        color="#333333",
        linewidth=1.5,
        linestyle="--",
        zorder=2,
    )

    operators_to_label = sorted(
        rows, key=lambda item: float(item["total_footprint"]), reverse=True
    )[: max(0, annotations)]

    # A dark ring distinguishes labeled points without using marker size as data.
    ax.scatter(
        [float(row["facility_count"]) for row in operators_to_label],
        [float(row["median_footprint"]) for row in operators_to_label],
        s=106,
        facecolors="none",
        edgecolors="#222222",
        linewidths=1.0,
        zorder=4,
    )

    for row in operators_to_label:
        operator = str(row["operator"])
        offset = LABEL_OFFSETS.get(operator, (12, 12))
        ax.annotate(
            operator,
            (float(row["facility_count"]), float(row["median_footprint"])),
            xytext=offset,
            textcoords="offset points",
            ha="right" if offset[0] < 0 else "left",
            va="center",
            fontsize=8.3,
            color="#222222",
            bbox={
                "boxstyle": "round,pad=0.16",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.92,
            },
            zorder=5,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(4.2, 430)
    ax.set_ylim(250, 80_000)
    ax.set_xticks([5, 10, 20, 50, 100, 200, 400])
    ax.set_yticks([300, 1_000, 3_000, 10_000, 30_000])
    ax.xaxis.set_major_formatter(FuncFormatter(comma_tick))
    ax.yaxis.set_major_formatter(FuncFormatter(comma_tick))
    ax.set_xlabel("Mapped facilities associated with operator")
    ax.set_ylabel("Median mapped footprint per facility (m²)")
    ax.grid(True, which="major", color="#D9D9D9", linewidth=0.8, alpha=0.8)
    ax.grid(True, which="minor", color="#ECECEC", linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    colorbar = fig.colorbar(scatter, ax=ax, pad=0.025, fraction=0.05)
    colorbar.set_label("Total mapped footprint (m²)", fontsize=10)
    colorbar.ax.yaxis.set_major_formatter(FuncFormatter(abbreviated_tick))
    colorbar.ax.tick_params(labelsize=9)
    colorbar.outline.set_visible(False)

    ax.text(
        0.02,
        0.96,
        f"Pearson r on log10 values = {correlation:.2f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        color="#444444",
    )

    fig.suptitle(
        "Operator portfolio scale and typical facility size",
        x=0.5,
        y=0.975,
        fontsize=18,
        fontweight="semibold",
    )
    fig.text(
        0.5,
        0.935,
        "Marker color represents total mapped footprint; both axes use logarithmic scales",
        ha="center",
        va="center",
        fontsize=11,
        color="#444444",
    )
    fig.text(
        0.5,
        0.022,
        f"{len(rows)} operators with at least {minimum_footprints} usable footprints. "
        "Medians and color totals exclude missing footprints; facility counts include all named records.",
        ha="center",
        va="center",
        fontsize=9,
        color="#555555",
    )

    fig.tight_layout(rect=(0.02, 0.055, 0.99, 0.91))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved chart to {output_path}")
    print(
        f"Included operators: {len(rows)}; unnamed facility records: {unnamed_rows}; "
        f"missing/invalid footprints among named records: {missing_footprints}; "
        f"log-scale Pearson r: {correlation:.3f}"
    )

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    args = parse_args()
    rows, unnamed_rows, missing_footprints = load_operator_rows(
        args.input, args.minimum_footprints
    )
    make_plot(
        rows,
        unnamed_rows,
        missing_footprints,
        args.minimum_footprints,
        args.output,
        args.annotate,
        args.show,
    )


if __name__ == "__main__":
    main()
