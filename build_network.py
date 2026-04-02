"""
build_network.py

Reads bibliography CSV files and builds co-authorship node/edge lists,
writing one xlsx per CSV (two sheets: Nodes and Edges) for use in the
SNA notebook.

Supported export formats: Google Scholar, Scopus, British Education Index,
Web of Science. Format is detected automatically from column names.


Put your CSV files in the same directory and run the script. Output xlsx
files will land in the same directory.
"""

import re
import itertools
from pathlib import Path

import pandas as pd
from openpyxl import Workbook


# ── Configuration ─────────────────────────────────────────────────────────────

INPUT_DIR  = Path(".")   # folder containing input CSV files
OUTPUT_DIR = Path(".")   # where to write the output xlsx files


# ── Format detection ──────────────────────────────────────────────────────────
# Each database exports authors in a different column position and uses
# different separators inside the author string.

def detect_format(filepath: Path) -> dict:
    df = pd.read_csv(filepath, encoding="latin-1")
    cols = df.columns.tolist()

    if cols[0] == "Authors" and cols[1] == "Title":
        fmt        = "google"
        author_col = "Authors"

    elif cols[0] == "Authors" and len(cols) > 2 and cols[2] == "Title":
        # Scopus inserts an extra column between Authors and Title
        fmt        = "scopus"
        author_col = "Authors"

    elif len(cols) > 1 and cols[1] == "Author":
        # British Education Index uses "Author" (singular) in column 2
        fmt        = "bei"
        author_col = "Author"

    else:
        # Web of Science: find the row that contains "Title" and re-read
        # from there so that row becomes the header
        with open(filepath, encoding="latin-1", errors="replace") as f:
            lines = f.readlines()
        start = next((i for i, l in enumerate(lines) if l.startswith("Title")), 0)
        df         = pd.read_csv(filepath, skiprows=start, encoding="latin-1")
        fmt        = "web"
        author_col = df.columns[1]   # WoS puts authors in column 2

    # Any column that isn't the author field or Title is a potential covariate
    cov_cols = [c for c in df.columns if c not in (author_col, "Title")]

    print(f"  {fmt} format detected in {filepath.name}")
    return {"fmt": fmt, "author_col": author_col, "cov_cols": cov_cols, "df": df}


# ── Name normalization ────────────────────────────────────────────────────────
# Reduces "Chen, Jack" → "Chen J" so the same person is recognized
# across papers even with minor name variations.

def _capitalize(s: str) -> str:
    return " ".join(w.capitalize() for w in s.split())


def shorten_name(name: str, field_sep: str, name_sep: str) -> str | None:
    """Split one author entry and return 'Last F' form."""
    name = name.strip()
    if not name:
        return None

    if name_sep == r"\.":
        # Scopus already gives "LastF." — just clean up capitalization
        return _capitalize(re.split(r"\.", name)[0])

    parts = [p.strip() for p in name.split(name_sep)]
    first_initial = parts[1].strip()[:1].upper() if len(parts) >= 2 else ""
    last = _capitalize(parts[0])
    return f"{last} {first_initial}".strip() if first_initial else last


def parse_authors(author_text: str, fmt: str) -> list[str]:
    """Split an author field string into shortened individual names."""
    if not isinstance(author_text, str) or not author_text.strip():
        return []

    if fmt == "scopus":
        field_sep, name_sep = ",", r"\."
    else:
        field_sep, name_sep = ";", ","

    raw = [a.strip() for a in author_text.split(field_sep)]
    return [n for a in raw if (n := shorten_name(a, field_sep, name_sep)) is not None]


# ── Build node and edge rows for one file ─────────────────────────────────────

def build_node_edge_lists(info: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    df         = info["df"]
    fmt        = info["fmt"]
    author_col = info["author_col"]
    cov_cols   = info["cov_cols"]

    node_rows = []
    edge_rows = []

    for paper_id, row in enumerate(df.itertuples(index=False), start=1):
        authors = parse_authors(getattr(row, author_col, ""), fmt)
        if not authors:
            continue

        for author in authors:
            entry = {"Author": author, "paper_id": paper_id}
            for col in cov_cols:
                entry[col] = getattr(row, col, None)
            node_rows.append(entry)

        # Every pair of co-authors on the same paper is an edge
        for a, b in itertools.combinations(authors, 2):
            edge_rows.append({"Source": a, "Target": b, "paper_id": paper_id})

    nodes_raw = pd.DataFrame(node_rows)
    edges_raw = pd.DataFrame(edge_rows)

    # One row per author; publication_count = distinct papers they appeared in
    final_nodes = (
        nodes_raw.groupby("Author")["paper_id"]
        .nunique()
        .reset_index(name="publication_count")
    )

    # For each covariate, attach the most frequent value per author
    # (an author can appear in many papers with slightly different metadata)
    for col in cov_cols:
        if col in nodes_raw.columns:
            valid = nodes_raw[nodes_raw[col].notna() & (nodes_raw[col] != "")]
            if valid.empty:
                continue
            modal = (
                valid.groupby(["Author", col])
                .size()
                .reset_index(name="n")
                .sort_values("n", ascending=False)
                .drop_duplicates("Author")
                [["Author", col]]
            )
            final_nodes = final_nodes.merge(modal, on="Author", how="left")

    # Edge weight = number of papers the two authors co-authored together
    final_edges = (
        edges_raw.groupby(["Source", "Target"])["paper_id"]
        .nunique()
        .reset_index(name="weight")
    )

    return final_nodes, final_edges


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    csv_files = sorted(INPUT_DIR.glob("*.csv"))
    print(f"{len(csv_files)} CSV file(s) found\n")

    for filepath in csv_files:
        print(f"Processing: {filepath.name}")
        info = detect_format(filepath)

        nodes, edges = build_node_edge_lists(info)
        print(f"  Nodes: {len(nodes)}  |  Edges: {len(edges)}")

        out_path = OUTPUT_DIR / filepath.name.replace(".csv", "_network.xlsx")
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            nodes.to_excel(writer, sheet_name="Nodes", index=False)
            edges.to_excel(writer, sheet_name="Edges", index=False)

        print(f"  Saved: {out_path}\n")


if __name__ == "__main__":
    main()
