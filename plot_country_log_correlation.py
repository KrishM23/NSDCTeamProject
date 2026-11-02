"""Plot the country-level relationship between data-center count and footprint.

Run from any directory:
    python3 plot_country_log_correlation.py

The chart is saved beside this script unless --output is supplied.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "clean_country_summary.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "country_facilities_vs_footprint_log.png"

CONTINENT_COLORS = {
    "Africa": "#D55E00",
    "Asia": "#E69F00",
    "Europe": "#0072B2",
    "North America": "#009E73",
    "Oceania": "#CC79A7",
    "South America": "#56B4E9",
}

LABEL_OFFSETS = {
    "United States of America": (8, 5),
    "France": (10, -1),
    "Germany": (10, -16),
    "United Kingdom": (10, 13),
    "Netherlands": (8, 8),
    "Australia": (8, 5),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a log-transformed scatter plot from the country summary."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--annotate",
        type=int,
        default=6,
        help="Number of countries with the most facilities to label.",
    )
    parser.add_argument(
        "--show", action="store_true", help="Also open the chart window."
    )
    return parser.parse_args()


def load_rows(csv_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        for record in csv.DictReader(file):
            try:
                facilities = float(record["osm_facilities"])
                footprint = float(record["total_footprint_m2"])
            except (TypeError, ValueError):
                continue

            # Logarithms are defined only for positive values.
            if facilities <= 0 or footprint <= 0:
                continue

            rows.append(
                {
                    "country": record["country"],
                    "continent": record["continent"],
                    "facilities": facilities,
                    "footprint": footprint,
                    "log_facilities": math.log10(facilities),
                    "log_footprint": math.log10(footprint),
                }
            )

    if len(rows) < 2:
        raise ValueError(
            "At least two complete, positive country records are required."
        )

    return rows


def correlation_and_line(rows: list[dict[str, object]]) -> tuple[float, float, float]:
    x = [float(row["log_facilities"]) for row in rows]
    y = [float(row["log_footprint"]) for row in rows]
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)

    sum_xy = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    sum_xx = sum((a - mean_x) ** 2 for a in x)
    sum_yy = sum((b - mean_y) ** 2 for b in y)

    correlation = sum_xy / math.sqrt(sum_xx * sum_yy)
    slope = sum_xy / sum_xx
    intercept = mean_y - slope * mean_x
    return correlation, slope, intercept


def make_plot(
    rows: list[dict[str, object]], output_path: Path, annotations: int, show: bool
) -> None:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["continent"])].append(row)

    correlation, slope, intercept = correlation_and_line(rows)

    fig, ax = plt.subplots(figsize=(10, 7))
    for continent in sorted(grouped):
        group = grouped[continent]
        ax.scatter(
            [row["log_facilities"] for row in group],
            [row["log_footprint"] for row in group],
            s=54,
            alpha=0.78,
            color=CONTINENT_COLORS.get(continent, "#777777"),
            edgecolor="white",
            linewidth=0.5,
            label=continent,
        )

    min_x = min(float(row["log_facilities"]) for row in rows)
    max_x = max(float(row["log_facilities"]) for row in rows)
    line_x = [min_x + (max_x - min_x) * i / 100 for i in range(101)]
    line_y = [intercept + slope * value for value in line_x]
    ax.plot(line_x, line_y, color="#333333", linewidth=1.5, linestyle="--")

    for row in sorted(rows, key=lambda item: float(item["facilities"]), reverse=True)[
        : max(0, annotations)
    ]:
        offset = LABEL_OFFSETS.get(str(row["country"]), (5, 5))
        ax.annotate(
            str(row["country"]),
            (float(row["log_facilities"]), float(row["log_footprint"])),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title(
        "Data-center facilities and total footprint by country\n"
        f"Pearson r on log10-transformed values = {correlation:.2f} (n = {len(rows)})"
    )
    ax.set_xlabel("log10(number of mapped data-center facilities)")
    ax.set_ylabel("log10(total mapped footprint in m²)")
    ax.set_xlim(min_x - 0.1, max_x + 0.55)
    ax.grid(True, color="#D9D9D9", linewidth=0.7, alpha=0.7)
    ax.set_axisbelow(True)
    ax.legend(title="Continent", frameon=False)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Saved chart to {output_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input)
    make_plot(rows, args.output, args.annotate, args.show)


if __name__ == "__main__":
    main()
