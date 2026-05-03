import glob
import io
import os
from typing import Optional

import pandas as pd

DEFAULT_COLUMNS = [
    "settore_codice",
    "LOB",
    "team",
    "Servizi A&M",
    "stato",
    "cliente_codice",
    "ricavo_2026",
    "ricavo_2025",
    "pipeline_lorda_2026",
    "pipeline_pesata_2026",
    "is_venduto",
]


def _empty_dataframe() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "settore_codice": pd.Series(dtype="string"),
            "LOB": pd.Series(dtype="string"),
            "team": pd.Series(dtype="string"),
            "Servizi A&M": pd.Series(dtype="string"),
            "stato": pd.Series(dtype="string"),
            "cliente_codice": pd.Series(dtype="string"),
            "ricavo_2026": pd.Series(dtype="float64"),
            "ricavo_2025": pd.Series(dtype="float64"),
            "pipeline_lorda_2026": pd.Series(dtype="float64"),
            "pipeline_pesata_2026": pd.Series(dtype="float64"),
            "is_venduto": pd.Series(dtype="bool"),
        }
    )
    return df


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for column in DEFAULT_COLUMNS:
        if column not in df.columns:
            if column == "is_venduto":
                df[column] = False
            elif column in ["ricavo_2026", "ricavo_2025", "pipeline_lorda_2026", "pipeline_pesata_2026"]:
                df[column] = 0.0
            else:
                df[column] = ""

    df["settore_codice"] = df["settore_codice"].astype(str).fillna("")
    df["LOB"] = df["LOB"].astype(str).fillna("")
    df["team"] = df["team"].astype(str).fillna("")
    df["Servizi A&M"] = df["Servizi A&M"].astype(str).fillna("")
    df["stato"] = df["stato"].astype(str).fillna("")
    df["cliente_codice"] = df["cliente_codice"].astype(str).fillna("")

    df["ricavo_2026"] = pd.to_numeric(df["ricavo_2026"], errors="coerce").fillna(0.0)
    df["ricavo_2025"] = pd.to_numeric(df["ricavo_2025"], errors="coerce").fillna(0.0)
    df["pipeline_lorda_2026"] = pd.to_numeric(df["pipeline_lorda_2026"], errors="coerce").fillna(0.0)
    df["pipeline_pesata_2026"] = pd.to_numeric(df["pipeline_pesata_2026"], errors="coerce").fillna(0.0)

    if df["is_venduto"].dtype != bool:
        df["is_venduto"] = df["is_venduto"].astype(bool)

    return df[DEFAULT_COLUMNS]


def load_and_prepare(source: Optional[object] = None) -> pd.DataFrame:
    if source is None:
        candidates = sorted(glob.glob("data/*.csv") + glob.glob("data/*.xlsx"))
        if not candidates:
            return _empty_dataframe()
        source = candidates[0]

    if hasattr(source, "read"):
        filename = getattr(source, "name", "").lower()
        try:
            source.seek(0)
        except Exception:
            pass

        content = source.read()
        if isinstance(content, str):
            content = content.encode("utf-8")

        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = _empty_dataframe()
    else:
        path = str(source)
        if path.lower().endswith(".csv"):
            df = pd.read_csv(path)
        elif path.lower().endswith(".xlsx"):
            df = pd.read_excel(path)
        else:
            df = _empty_dataframe()

    return _normalize_dataframe(df)


def kpi_overview(df: pd.DataFrame) -> dict:
    venduto_2026 = df.loc[df["is_venduto"], "ricavo_2026"].sum()
    venduto_2025 = df.loc[df["is_venduto"], "ricavo_2025"].sum()
    pipeline_lorda_2026 = df["pipeline_lorda_2026"].sum()
    pipeline_pesata_2026 = df["pipeline_pesata_2026"].sum()

    closed_states = {
        "venduta",
        "chiusa",
        "closed",
        "closed won",
        "closed lost",
        "persa",
        "eliminata",
    }
    closed = df[df["stato"].str.lower().isin(closed_states)]
    lost = closed[closed["stato"].str.lower().isin({"persa", "eliminata", "closed lost"})]

    closed_count = len(closed)
    conversion_rate_closed = venduto_2026 / closed_count if closed_count else 0.0
    lost_rate_closed = len(lost) / closed_count if closed_count else 0.0

    return {
        "venduto_2026": venduto_2026,
        "venduto_2025": venduto_2025,
        "pipeline_lorda_2026": pipeline_lorda_2026,
        "pipeline_pesata_2026": pipeline_pesata_2026,
        "conversion_rate_closed": conversion_rate_closed,
        "lost_rate_closed": lost_rate_closed,
    }
