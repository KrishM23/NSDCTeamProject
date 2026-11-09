"""Compare each continent's share of facilities with its share of footprint.

Run from any directory:
    uv run --with matplotlib python plot_regional_facility_vs_footprint_share.py
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
DEFAULT_INPUT = PROJECT_DIR / "clean_data_centers.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "regional_facility_vs_footprint_share.png"

CONTINENT_COLORS = {
    "Africa": "#D55E00",
    "Asia": "#E69F00",
    "Europe": "#0072B2",
    "North America": "#009E73",
    "Oceania": "#CC79A7",
    "South America": "#56B4E9",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare continent shares of facilities and total mapped footprint."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show", action="store_true", help="Also open the chart window.")
    return parser.parse_args()


def load_shares(
    csv_path: Path,
) -> tuple[list[dict[str, object]], int, int]:
    facility_counts: Counter[str] = Counter()
    footprint_totals: Counter[str] = Counter()
    missing_or_invalid = 0
    outside_scope = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"continent", "footprint_area_m2"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "The input CSV must contain continent and footprint_area_m2."
            )

        for record in reader:
            continent = record["continent"].strip()
            if continent not in CONTINENT_COLORS:
                outside_scope += 1
                continue

            try:
                footprint = float(record["footprint_area_m2"])
            except (TypeError, ValueError):
                missing_or_invalid += 1
                continue

            if not math.isfinite(footprint) or footprint <= 0:
                missing_or_invalid += 1
                continue

            # Both shares use exactly the same complete-case facility records.
            facility_counts[continent] += 1
            footprint_totals[continent] += footprint

    total_facilities = sum(facility_counts.values())
    total_footprint = sum(footprint_totals.values())
    if total_facilities == 0 or total_footprint <= 0:
        raise ValueError("No complete, positive footprint records were found.")

    rows = []
    for continent in CONTINENT_COLORS:
        if facility_counts[continent] == 0:
            continue
        rows.append(
            {
                "continent": continent,
                "count": facility_counts[continent],
                "facility_share": facility_counts[continent] / total_facilities,
                "footprint_share": footprint_totals[continent] / total_footprint,
            }
        )

    rows.sort(key=lambda row: float(row["footprint_share"]), reverse=True)
    return rows, missing_or_invalid, outside_scope


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


def make_plot(
    rows: list[dict[str, object]],
    missing_or_invalid: int,
    outside_scope: int,
    output_path: Path,
    show: bool,
) -> None:
    configure_typography()
    fig, ax = plt.subplots(figsize=(11, 7.2))
    y_positions = list(range(len(rows)))

    for y, row in zip(y_positions, rows):
        continent = str(row["continent"])
        facility_share = float(row["facility_share"])
        footprint_share = float(row["footprint_share"])
        color = CONTINENT_COLORS[continent]

        ax.plot(
            [facility_share, footprint_share],
            [y, y],
            color=color,
            linewidth=4.2,
            alpha=0.38,
            solid_capstyle="round",
            zorder=1,
        )
        ax.scatter(
            facility_share,
            y,
            s=112,
            marker="o",
            facecolor="white",
            edgecolor=color,
            linewidth=2.2,
            zorder=3,
        )
        ax.scatter(
            footprint_share,
            y,
            s=105,
            marker="D",
            facecolor=color,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )

        facility_is_left = facility_share <= footprint_share
        gap = abs(facility_share - footprint_share)

        if gap < 0.02:
            # Very close markers need vertical separation instead of two
            # percentage labels competing for the same horizontal space.
            facility_offset = (6, 15)
            footprint_offset = (6, -15)
            facility_alignment = footprint_alignment = "left"
        elif min(facility_share, footprint_share) < 0.02:
            # Keep a very small share label inside the plotting area rather
            # than allowing it to collide with the continent label.
            if facility_share < footprint_share:
                facility_offset = (0, -15)
                footprint_offset = (9, 0)
                facility_alignment = "center"
                footprint_alignment = "left"
            else:
                facility_offset = (9, 0)
                footprint_offset = (0, -15)
                facility_alignment = "left"
                footprint_alignment = "center"
        else:
            facility_offset = (-9 if facility_is_left else 9, 0)
            footprint_offset = (9 if facility_is_left else -9, 0)
            facility_alignment = "right" if facility_is_left else "left"
            footprint_alignment = "left" if facility_is_left else "right"

        ax.annotate(
            f"{facility_share:.1%}",
            (facility_share, y),
            xytext=facility_offset,
            textcoords="offset points",
            ha=facility_alignment,
            va="center",
            fontsize=9,
            color="#333333",
        )
        ax.annotate(
            f"{footprint_share:.1%}",
            (footprint_share, y),
            xytext=footprint_offset,
            textcoords="offset points",
            ha=footprint_alignment,
            va="center",
            fontsize=9,
            fontweight="bold",
            color="#333333",
        )

    labels = [
        f"{row['continent']}\n(n={int(row['count']):,})"
        for row in rows
    ]
    ax.set_yticks(y_positions, labels=labels)
    for tick_label, row in zip(ax.get_yticklabels(), rows):
        tick_label.set_color(CONTINENT_COLORS[str(row["continent"])])
        tick_label.set_fontweight("semibold")

    ax.invert_yaxis()
    ax.set_xlim(0, 0.66)
    ax.set_xlabel("Share of six-continent total")
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.grid(True, axis="x", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=10)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="white",
            markeredgecolor="#444444",
            markeredgewidth=1.8,
            markersize=8,
            label="Facility share",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="none",
            markerfacecolor="#444444",
            markeredgecolor="white",
            markersize=8,
            label="Footprint share",
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower right",
        frameon=False,
        ncol=2,
        fontsize=10,
    )

    usable_count = sum(int(row["count"]) for row in rows)
    fig.suptitle(
        "Regional share of data centers and mapped footprint",
        x=0.5,
        y=0.975,
        fontsize=18,
        fontweight="semibold",
    )
    fig.text(
        0.5,
        0.93,
        "A larger footprint share than facility share indicates larger mapped sites on average",
        ha="center",
        va="center",
        fontsize=11,
        color="#444444",
    )
    fig.text(
        0.5,
        0.022,
        f"Both shares use the same {usable_count:,} facilities with positive footprints. "
        f"{missing_or_invalid:,} missing or invalid footprints and {outside_scope:,} out-of-scope rows were excluded.",
        ha="center",
        va="center",
        fontsize=9,
        color="#555555",
    )

    fig.tight_layout(rect=(0.03, 0.06, 0.99, 0.90))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved chart to {output_path}")
    print(
        f"Complete-case facilities: {usable_count}; missing/invalid: "
        f"{missing_or_invalid}; out of scope: {outside_scope}"
    )
    for row in rows:
        print(
            f"{row['continent']}: facility share={float(row['facility_share']):.3%}, "
            f"footprint share={float(row['footprint_share']):.3%}"
        )

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    args = parse_args()
    rows, missing_or_invalid, outside_scope = load_shares(args.input)
    make_plot(rows, missing_or_invalid, outside_scope, args.output, args.show)


if __name__ == "__main__":
    main()
