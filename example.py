"""Show how two weighting rules respond to the same component prices."""

import pandas as pd
from index_math import construct_index


def component_prices():
    return pd.DataFrame(
        {
            "Dates": pd.date_range("2024-01-01", periods=6, freq="MS"),
            "Firm A": [100, 108, 112, 105, 116, 120],
            "Firm B": [100, 98, 95, 102, 102, 100],
            "Firm C": [100, 101, 102, 103, 102, 104],
        }
    )


def compare():
    prices = component_prices()
    paths = {}
    for name, values in [("Equal weight", [1 / 3, 1 / 3, 1 / 3]), ("60/25/15", [0.60, 0.25, 0.15])]:
        weights = pd.DataFrame({"Ticker": ["Firm A", "Firm B", "Firm C"], "Weight": values})
        index = construct_index(prices, weights).set_index("Dates")
        paths[name] = index["Index_Value"]
    return pd.DataFrame(paths)


if __name__ == "__main__":
    print(compare().round(2).to_string())
