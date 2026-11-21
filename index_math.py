"""Construct a base-100 index from normalised component prices and fixed weights."""
import pandas as pd


def construct_index(prices, weights):
    quotes = prices.melt(id_vars="Dates", var_name="Ticker", value_name="Price")
    # A ticker can appear in two sleeves. Combine its allocations before pricing the index.
    allocations = weights.groupby("Ticker", as_index=False, sort=False)["Weight"].sum(min_count=1)
    matched = quotes.merge(allocations, on="Ticker", how="inner", validate="many_to_one")
    # Keep the weight on its own ticker even when price columns arrive in another order.
    matched["Weighted_Price"] = matched["Price"] * matched["Weight"]
    index = matched.groupby("Dates")["Weighted_Price"].sum(min_count=1).rename("Index_Value").reset_index()
    if index.empty or pd.isna(index.loc[0, "Index_Value"]) or index.loc[0, "Index_Value"] == 0:
        raise ValueError("The index needs a nonzero starting value for the matched constituents.")
    index["Index_Value"] = 100 * index["Index_Value"] / index.loc[0, "Index_Value"]
    return index

