"""Plot a heatmap of leading operators' mapped facilities by continent.

Run from any directory:
    uv run --with matplotlib python plot_operator_presence_by_continent.py
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.ticker import FuncFormatter


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
DEFAULT_INPUT = PROJECT_DIR / "clean_data_centers.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "operator_presence_by_continent.png"

CONTINENTS = [
    "North America",
    "Europe",
    "Asia",
    "Oceania",
    "South America",
    "Africa",
]

CONTINENT_COLORS = {
    "Africa": "#D55E00",
    "Asia": "#E69F00",
    "Europe": "#0072B2",
    "North America": "#009E73",
    "Oceania": "#CC79A7",
    "South America": "#56B4E9",
}

COUNT_CMAP = LinearSegmentedColormap.from_list(
    "operator_count_blue", ["#EAF4FA", "#56B4E9", "#0072B2", "#17365D"]
)
COUNT_CMAP.set_bad("#F1F1F1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a continent heatmap for leading named operators."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of operators to show, ranked by mapped facility count.",
    )
    parser.add_argument("--show", action="store_true", help="Also open the chart window.")
    return parser.parse_args()


def load_operator_counts(
    csv_path: Path, top_n: int
) -> tuple[list[str], list[list[int]], list[int], int, int]:
    if top_n < 1:
        raise ValueError("--top must be at least 1.")

    operator_counts: dict[str, Counter[str]] = defaultdict(Counter)
    unnamed_rows = 0
    out_of_scope_rows = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"operator", "continent"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("The input CSV must contain operator and continent.")

        for record in reader:
            continent = record["continent"].strip()
            if continent not in CONTINENTS:
                out_of_scope_rows += 1
                continue

            operator = record["operator"].strip()
            if not operator:
                unnamed_rows += 1
                continue

            operator_counts[operator][continent] += 1

    ranked = sorted(
        operator_counts,
        key=lambda operator: sum(operator_counts[operator].values()),
        reverse=True,
    )[:top_n]
    if not ranked:
        raise ValueError("No named operator records were found.")

    matrix = [
        [operator_counts[operator][continent] for continent in CONTINENTS]
        for operator in ranked
    ]
    totals = [sum(row) for row in matrix]
    return ranked, matrix, totals, unnamed_rows, out_of_scope_rows


def configure_typography() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "text.color": "#222222",
            "xtick.color": "#444444",
            "ytick.color": "#444444",
        }
    )


def integer_tick(value: float, _position: int) -> str:
    return f"{value:,.0f}"


def make_plot(
    operators: list[str],
    matrix: list[list[int]],
    totals: list[int],
    unnamed_rows: int,
    out_of_scope_rows: int,
    output_path: Path,
    show: bool,
) -> None:
    configure_typography()
    values = np.asarray(matrix, dtype=float)
    masked_values = np.ma.masked_equal(values, 0)
    max_count = int(values.max())
    norm = LogNorm(vmin=1, vmax=max_count)

    fig, ax = plt.subplots(figsize=(11, 8.5))
    image = ax.imshow(
        masked_values,
        cmap=COUNT_CMAP,
        norm=norm,
        aspect="auto",
        interpolation="none",
    )

    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            count = int(values[row_index, column_index])
            if count == 0:
                label = "—"
                color = "#999999"
            else:
                label = f"{count:,}"
                color = "white" if norm(count) >= 0.58 else "#222222"
            ax.text(
                column_index,
                row_index,
                label,
                ha="center",
                va="center",
                fontsize=9,
                fontweight="semibold" if count else "normal",
                color=color,
            )

    x_labels = [continent.replace(" ", "\n") for continent in CONTINENTS]
    y_labels = [
        f"{operator}  ({total:,})" for operator, total in zip(operators, totals)
    ]
    ax.set_xticks(range(len(CONTINENTS)), labels=x_labels)
    ax.set_yticks(range(len(operators)), labels=y_labels)
    ax.tick_params(axis="x", which="major", pad=9, length=0)
    ax.tick_params(axis="y", which="major", pad=8, length=0)
    ax.xaxis.tick_top()

    for tick_label, continent in zip(ax.get_xticklabels(), CONTINENTS):
        tick_label.set_color(CONTINENT_COLORS[continent])
        tick_label.set_fontweight("semibold")

    ax.set_xticks(np.arange(-0.5, len(CONTINENTS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(operators), 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    colorbar = fig.colorbar(image, ax=ax, pad=0.025, fraction=0.035)
    colorbar.set_label("Mapped facility count", fontsize=10)
    candidate_ticks = [1, 3, 10, 30, 100, 200]
    colorbar.set_ticks([tick for tick in candidate_ticks if tick <= max_count])
    colorbar.ax.yaxis.set_major_formatter(FuncFormatter(integer_tick))
    colorbar.ax.tick_params(labelsize=9)
    colorbar.outline.set_visible(False)

    fig.suptitle(
        "Mapped operator presence by continent",
        x=0.5,
        y=0.975,
        fontsize=18,
        fontweight="semibold",
    )
    fig.text(
        0.5,
        0.935,
        f"Facility counts for the {len(operators)} largest named operator portfolios",
        ha="center",
        va="center",
        fontsize=11,
        color="#444444",
    )
    fig.text(
        0.5,
        0.022,
        f"Operators are ranked by total mapped facilities, shown in parentheses. "
        f"{unnamed_rows:,} records without an operator and {out_of_scope_rows:,} out-of-scope rows were excluded. "
        "A dash means no facility was mapped in this dataset.",
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
        f"Operators shown: {len(operators)}; unnamed records: {unnamed_rows}; "
        f"out of scope: {out_of_scope_rows}"
    )

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    args = parse_args()
    results = load_operator_counts(args.input, args.top)
    make_plot(*results, args.output, args.show)


if __name__ == "__main__":
    main()
