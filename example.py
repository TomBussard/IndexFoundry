"""Show how two weighting rules respond to the same component prices."""

import pandas as pd
from index_math import construct_index, normalize_prices, rebalance_index


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


def linked_basket():
    """Link a new 20/60/20 basket to the previous segment's final close."""
    prices = component_prices()
    tickers = prices.columns.drop("Dates")
    weights = pd.DataFrame({"Ticker": tickers, "Weight": [0.60, 0.25, 0.15]})
    first = construct_index(normalize_prices(prices.iloc[:3]), weights)
    next_prices = normalize_prices(prices.iloc[3:].reset_index(drop=True))
    next_caps = pd.DataFrame({"Ticker": tickers, "CUR_MKT_CAP": [20, 60, 20]})
    return rebalance_index(first, next_prices, next_caps).set_index("Dates")["Index_Value"]


if __name__ == "__main__":
    paths = compare()
    paths["Rebalanced to 20/60/20"] = linked_basket()
    print(paths.round(2).to_string())
