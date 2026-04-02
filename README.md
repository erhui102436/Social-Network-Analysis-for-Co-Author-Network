# Co-authorship Network Analysis for Systematic Reviews

A two-script Python pipeline that builds and visualizes co-authorship networks from bibliography exports. Parses CSV files from four major academic databases, constructs weighted co-authorship graphs, detects research communities, and produces publication-quality network figures.

---

## Overview

Given a set of bibliography CSV files from a systematic review, this pipeline:

1. Parses author metadata and builds weighted node/edge lists
2. Constructs a co-authorship graph where nodes are authors and edges represent co-authored papers
3. Detects research communities using the Louvain algorithm
4. Generates two network figures per dataset — one labeled with author names, one with node attributes

---

## Pipeline

```
bibliography CSVs  →  build_network.py  →  *_network.xlsx  →  SNA_notebook.ipynb  →  figures
```

**Step 1 — `build_network.py`**
Reads bibliography CSV files and outputs one Excel workbook per CSV with two sheets:
- `Nodes` — one row per author with publication count and any available covariates
- `Edges` — one row per co-authorship pair with edge weight (number of co-authored papers)

**Step 2 — `SNA_method_for_systematic_review.ipynb`**
Reads the Excel files, builds a NetworkX graph, runs community detection, and saves two figures per dataset.

---

## Supported Database Formats

Format is detected automatically from column structure:

| Database | Detection method |
|---|---|
| Google Scholar | First column = `Authors`, second = `Title` |
| Scopus | First column = `Authors`, third = `Title` |
| British Education Index | Second column = `Author` (singular) |
| Web of Science | Header row starts with `Title` |

---

## Output Figures

Two PNG figures are saved per dataset:

**Figure 1 — Author names view** (`*_names.png`)
Top 3 highest-degree authors per community are labeled by name. Node size scales with weighted degree. Intra-community edges shown as dashed colored lines; inter-community edges as faint curved lines.

**Figure 2 — Node attributes view** (`*_attributes.png`)
Same layout; top nodes labeled with their first available covariate value (e.g., publication count, year, research area) instead of names. Useful for identifying attribute patterns within and across communities.

Both figures use a community-aware two-level layout: communities are first positioned relative to each other, then internal nodes are laid out within each community to keep clusters visually separate.

---

## Repository Structure

```
co-authorship-sna/
│
├── build_network.py                        # Step 1: CSV → xlsx
├── SNA_method_for_systematic_review.ipynb  # Step 2: xlsx → figures
│
├── data/
│   └── README.md          # Data format description (no raw data included)
│
├── outputs/
│   └── figures/           # Generated PNG files land here
│
├── requirements.txt
└── README.md
```

---

## Requirements

```
networkx>=3.0
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
openpyxl>=3.1
python-louvain>=0.16
```

Install all dependencies:

```bash
pip install -r requirements.txt
```

> **Note:** `python-louvain` provides the Louvain community detection algorithm. If it is not installed, the pipeline automatically falls back to NetworkX's built-in greedy modularity algorithm.

---

## How to Run

**Step 1: Prepare your bibliography CSV**

Export your literature search results from Google Scholar, Scopus, Web of Science, or British Education Index as CSV files. Place them in the project root directory.

Your CSV must include at minimum:
- A paper title column
- An author list column (authors separated by semicolons or commas depending on database)

**Step 2: Build the network files**

```bash
python build_network.py
```

This reads all `*.csv` files in the current directory and writes one `*_network.xlsx` file per CSV.

**Step 3: Run the analysis notebook**

Open `SNA_method_for_systematic_review.ipynb` in Jupyter and update the `NETWORK_FILES` dictionary to point to your xlsx files:

```python
NETWORK_FILES = {
    "your_dataset": "your_dataset_network.xlsx"
}
```

Run all cells. Two PNG figures will be saved for each dataset.

---

## Data Availability

This repository contains only code. The bibliography data used in the original analysis is not included due to copyright restrictions on exported database records.

To replicate with your own data, export bibliography records from any supported database (Google Scholar, Scopus, Web of Science, British Education Index) and follow the steps above.

---

## Key Methods

**Name normalization**
Author names are standardized to `Last F` format (e.g., `Zhang H`) to match the same person across papers despite minor variations in how databases format names.

**Edge weighting**
Edge weight between two authors equals the number of papers they co-authored together in the corpus. Node weighted degree is the sum of all edge weights for that author.

**Community detection**
Louvain algorithm optimizes modularity to find densely connected author clusters. Communities with fewer than 2 members are removed. Community IDs are renumbered 1, 2, 3… for consistency across runs.

**Layout**
Two-level force-directed layout: community positions are computed first using circular or spring layout on a meta-graph, then internal nodes are positioned within each community using spring layout with a community-specific seed for reproducibility.
