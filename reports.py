"""Build report images in the current Streamlit session."""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import matplotlib.pyplot as plt
import streamlit as st


def save_figure(fig, filename):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    st.session_state["report_images"][Path(filename).name] = buffer.getvalue()
    plt.close(fig)


def dataframe_to_image(df, filename, decimals=2):
    rounded = df.round(decimals)
    fig, ax = plt.subplots(figsize=(min(15, 5 + 0.5 * len(df.columns)), 1 + 0.5 * len(df)))
    ax.axis("off")
    table = ax.table(
        cellText=rounded.values, colLabels=rounded.columns, cellLoc="center", loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(range(len(df.columns)))
    save_figure(fig, filename)


def create_zip():
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, contents in st.session_state["report_images"].items():
            archive.writestr(name, contents)
    buffer.seek(0)
    return buffer
