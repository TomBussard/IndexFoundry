"""Launch the public example or open the original workbook analysis."""

import pandas as pd
import streamlit as st

from example import compare, component_prices
from index_math import construct_index
from workbook import DEFAULT_FILE


def weighting_study():
    st.title("IndexFoundry")
    st.write(
        "How much of an index move comes from the companies you picked, and how much from their weights?"
    )
    prices = component_prices()
    st.caption("Six monthly observations for three fictional companies. All series start at 100.")
    st.dataframe(prices.set_index("Dates"), use_container_width=True)
    percent = st.slider("Starting weight of Firm A (%)", 0, 100, 60)
    rest = (100 - percent) / 100
    weights = pd.DataFrame(
        {"Ticker": prices.columns[1:], "Weight": [percent / 100, rest * 5 / 8, rest * 3 / 8]}
    )
    reference = compare()["Equal weight"]
    custom = construct_index(prices, weights).set_index("Dates")["Index_Value"]
    series = pd.concat([reference, custom.rename("Your allocation")], axis=1)
    st.line_chart(series)
    left, right = st.columns(2)
    left.metric("Equal-weight final level", f"{reference.iloc[-1]:.2f}")
    right.metric("Your final level", f"{custom.iloc[-1]:.2f}")
    st.caption(
        "The remaining weight is split 5:3 between Firms B and C. The workbook study adds sectors, currencies and rebalancing."
    )
    st.download_button(
        "Download index levels", series.to_csv(), "index-levels.csv", mime="text/csv"
    )


st.set_page_config(page_title="IndexFoundry", layout="wide")
st.navigation(
    [
        st.Page(weighting_study, title="Weighting study", default=not DEFAULT_FILE.is_file()),
        st.Page("workbench.py", title="Workbook analysis", default=DEFAULT_FILE.is_file()),
    ]
).run()
