"""Construct a base-100 index from normalised component prices and fixed weights."""

import pandas as pd


def construct_index(prices, weights):
    quotes = prices.melt(id_vars="Dates", var_name="Ticker", value_name="Price")
    # A ticker can appear in two sleeves. Combine its allocations before pricing the index.
    allocations = weights.groupby("Ticker", as_index=False, sort=False)["Weight"].sum(min_count=1)
    matched = quotes.merge(allocations, on="Ticker", how="inner", validate="many_to_one")
    # Keep the weight on its own ticker even when price columns arrives in another order.
    matched["Weighted_Price"] = matched["Price"] * matched["Weight"]
    index = (
        matched.groupby("Dates")["Weighted_Price"]
        .sum(min_count=1)
        .rename("Index_Value")
        .reset_index()
    )
    if index.empty or pd.isna(index.loc[0, "Index_Value"]) or index.loc[0, "Index_Value"] == 0:
        raise ValueError("The index needs a nonzero starting value for the matched constituents.")
    index["Index_Value"] = 100 * index["Index_Value"] / index.loc[0, "Index_Value"]
    return index


def merge_dates(spx_prices, sxxp_prices):
    """Merge two DataFrames on common dates."""
    # Formatting dates
    spx_prices["Dates"] = pd.to_datetime(spx_prices["Dates"])
    sxxp_prices["Dates"] = pd.to_datetime(sxxp_prices["Dates"])

    # Fusion on dates
    merged_data_frame = pd.merge(spx_prices, sxxp_prices, on="Dates", how="inner")

    return merged_data_frame


def normalize_prices(dataframe):
    """Normalizes the columns of a DataFrame
    dividing each value by the first non-NaN value of the column."""
    normalize_df = dataframe.copy()
    for col in normalize_df.columns:
        if col != "Dates":
            first_value = normalize_df[col].dropna().iloc[0]
            normalize_df[col] = normalize_df[col] / first_value
    return normalize_df


def market_cap_weights(index_prices, qualitativ_data):
    """Allocate to constituents with a quoted price and a positive market capitalisation."""
    caps = pd.to_numeric(qualitativ_data["CUR_MKT_CAP"], errors="coerce")
    table = pd.DataFrame({"Ticker": qualitativ_data.iloc[:, 0], "Market cap": caps})
    table = table[table["Ticker"].isin(index_prices.columns.drop("Dates")) & (caps > 0)]
    caps = table.groupby("Ticker", sort=False)["Market cap"].sum()
    if caps.empty:
        return pd.DataFrame(columns=["Ticker", "Weight"])
    return (caps / caps.sum()).rename("Weight").reset_index()


def rebalance_index(previous_index, processed_prices, qualitativ_data):
    """Chain the eligible basket to the previous closing level at the first new observation."""
    dates = pd.to_datetime(processed_prices["Dates"])
    fresh = processed_prices.loc[dates > pd.to_datetime(previous_index["Dates"]).max()]
    if fresh.empty:
        return previous_index.copy()
    weights = market_cap_weights(fresh, qualitativ_data)
    if weights.empty:
        return previous_index.copy()
    segment = construct_index(fresh, weights)
    segment["Index_Value"] *= previous_index["Index_Value"].iloc[-1] / 100
    return pd.concat([previous_index, segment], ignore_index=True)


def prepare_reference_index(index_data, column_name, date_column="PX_LAST", *, base_100=False):
    """Align the selected benchmark, optionally rebasing its first valid level to 100."""
    frame = index_data[[date_column, column_name]].copy()
    frame.columns = ["Dates", "Index_Value"]
    frame["Dates"] = pd.to_datetime(frame["Dates"], format="%d/%m/%Y", errors="coerce")
    frame["Index_Value"] = pd.to_numeric(
        frame["Index_Value"].astype(str).str.replace(",", "."), errors="coerce"
    )
    frame = frame.dropna().sort_values("Dates")
    if base_100 and not frame.empty:
        frame = adjust_to_base_100(frame, ["Index_Value"])
    return frame


def adjust_to_base_100(df, columns):
    """Adjusts the specified columns of a DataFrame to start exactly at 100."""
    adjusted_df = df.copy()
    for col in columns:
        first_value = adjusted_df[col].iloc[0]
        adjusted_df[col] = (adjusted_df[col] / first_value) * 100
    return adjusted_df


def weights_scores(score_data, top_n="all"):
    """Calculate the standard weights based on the calculated scores for each company.
    May limit the number of companies kept to the highest scores."""
    if top_n != "all":
        score_data = score_data.nlargest(top_n, "Score")

    score_data = score_data.copy()
    total_score = score_data["Score"].sum()
    score_data["Weight"] = score_data["Score"] / total_score

    return score_data[["Ticker", "Weight"]].sort_values(by="Weight", ascending=False)
