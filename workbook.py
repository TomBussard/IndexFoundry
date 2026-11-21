"""Read the sheets used by the historical index workbench."""

from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
import streamlit as st

DEFAULT_FILE = Path("Data projet indices python.xlsx")
SHEETS = {
    "index_data": "Index",
    "forex_data": "Forex",
    "members_data": "Members",
    "spx_prices": "SPX_PX_LAST",
    "sxxp_prices": "SXXP_PX_LAST",
    "qualitativ_2018": "Qualitativ_2018",
    "qualitativ_2019": "Qualitativ_2019",
    "qualitativ_2020": "Qualitativ_2020",
}


@st.cache_data(show_spinner=False, max_entries=3)
def read_workbook(content):
    from io import BytesIO

    with pd.ExcelFile(BytesIO(content), engine="openpyxl") as book:
        missing = set(SHEETS.values()) - set(book.sheet_names)
        if missing:
            raise ValueError("Missing sheets: " + ", ".join(sorted(missing)))
        frames = {key: book.parse(sheet) for key, sheet in SHEETS.items()}
    # The original provider file leaves the identifier column unnamed in some years.
    for key in ("qualitativ_2018", "qualitativ_2019", "qualitativ_2020"):
        if "Ticker" not in frames[key]:
            frames[key]["Ticker"] = frames[key].iloc[:, 0]
    return frames


def select_workbook():
    st.title("Equity index workbench")
    uploaded = st.file_uploader("Select the source workbook", type=["xlsx"])
    if uploaded is None and not DEFAULT_FILE.is_file():
        st.info(
            "Use a workbook with the eight sheets listed below. The weighting study runs without a file."
        )
        st.write(", ".join(SHEETS.values()))
        st.stop()
    content = uploaded.getvalue() if uploaded is not None else DEFAULT_FILE.read_bytes()
    try:
        return read_workbook(content)
    except (ValueError, OSError, BadZipFile) as error:
        st.error(f"Could not read this workbook. {error}")
        st.stop()
