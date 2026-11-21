"""Sector, style and benchmark studies on a supplied eight-sheet workbook."""

import urllib.parse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from index_math import (
    adjust_to_base_100,
    construct_index,
    market_cap_weights,
    merge_dates,
    normalize_prices,
    weights_scores,
    rebalance_index,
    prepare_reference_index,
)
from reports import create_zip, dataframe_to_image, save_figure
from workbook import select_workbook

donnees = select_workbook()
st.session_state["report_images"] = {}


# Section Sector index
st.header("Sector index")

st.write(
    "Select a sector and a date range to compare US and European constituents with the two benchmarks."
)

# Management of missing data or errors
if "members_data" not in donnees or donnees["members_data"] is None:
    st.error("'Members' data are not available. Check the Excel file.")
    st.stop()

members_data = donnees["members_data"]
spx_prices = donnees.get("spx_prices", None)
sxxp_prices = donnees.get("sxxp_prices", None)

if spx_prices is None or sxxp_prices is None:
    st.error("Price data for SPX or SXXP are not available. Check the Excel file.")
    st.stop()

# Single list of available sectors
secteurs_disponibles = members_data["BICS_LEVEL_1_SECTOR_NAME"].dropna().unique()

# Selecting the sector by the user
st.sidebar.header("Filter by sector")
secteur_choisi = st.sidebar.selectbox("Choose a sector:", options=secteurs_disponibles)

# Filter companies by sector selected
entreprises_filtrees = members_data[members_data["BICS_LEVEL_1_SECTOR_NAME"] == secteur_choisi]

# Single list of sub-sectors available for the selected sector
sous_secteurs_disponibles = (
    entreprises_filtrees["SPX_BICS_LEVEL_4_SUB_INDUSTRY_NAME"].dropna().unique()
)

# Selection of subsectors
sous_secteurs_choisis = st.sidebar.multiselect(
    "Select the sub-sectors:", options=sous_secteurs_disponibles
)

# Filter enterprises by selected subsectors
if sous_secteurs_choisis:
    entreprises_filtrees = entreprises_filtrees[
        entreprises_filtrees["SPX_BICS_LEVEL_4_SUB_INDUSTRY_NAME"].isin(sous_secteurs_choisis)
    ]

# Show filtered results
st.subheader(f" Companies in sector '{secteur_choisi}'")
st.write("**Selected companies:**")
st.dataframe(entreprises_filtrees)

# Show unique tickers for SPX and SXXP
spx_tickers = entreprises_filtrees["SPX Index"].dropna().unique()
sxxp_tickers = entreprises_filtrees["SXXP Index"].dropna().unique()

st.write("**US Tickers (SPX):**", spx_tickers)
st.write("**European tickers (SXXP):**", sxxp_tickers)


# Function to filter prices
def filter_prices(
    sheet_prices,
    tickers,
    start_date,
    end_date,
    max_consecutive_nans=10,
    min_valid_ratio=0.5,
    verbose=False,
):
    """Filter the prices for the given tickers and within a specified date range.
    Includes only columns that meet the criteria:
    - Minimum proportion of valid data.
    - Maximum number of consecutive NaNs."""
    sheet_prices["Dates"] = pd.to_datetime(sheet_prices["Dates"])

    # Filter by date range
    filtered_prices = sheet_prices[
        (sheet_prices["Dates"] >= pd.to_datetime(start_date))
        & (sheet_prices["Dates"] <= pd.to_datetime(end_date))
    ].copy()

    columns = ["Dates"]  # Colonne Dates incluse
    excluded_tickers = []  # List of excluded tickers

    for ticker in tickers:
        if ticker in filtered_prices.columns:
            # Check the proportion of valid data
            valid_data_ratio = filtered_prices[ticker].notna().sum() / len(filtered_prices[ticker])

            # Exclude tickers with too few valid data
            if valid_data_ratio < min_valid_ratio:
                excluded_tickers.append(
                    (ticker, f"Less than {min_valid_ratio * 100}% valid prices")
                )
                if verbose:
                    st.write(
                        f" {ticker} excluded : Less than {min_valid_ratio * 100}% valid prices"
                    )
                continue

            # Check for consecutive NaNs
            nan_count = (
                filtered_prices[ticker]
                .isna()
                .astype(int)
                .rolling(window=max_consecutive_nans)
                .sum()
            )
            if (nan_count >= max_consecutive_nans).any():
                excluded_tickers.append(
                    (ticker, f"At least {max_consecutive_nans} consecutive missing prices")
                )
                if verbose:
                    st.write(
                        f" {ticker} excluded : At least {max_consecutive_nans} consecutive missing prices"
                    )
                continue

            # Add the ticker if it meets the criteria
            columns.append(ticker)

    # Filter valid columns
    filtered_prices = filtered_prices[columns]

    # Fill the remaining NaNs with known values (forward and backward fill)
    filtered_prices = filtered_prices.ffill().bfill()

    if verbose:
        st.write(f" Nombre d'entreprises incluses : {len(columns) - 1}")
        st.write(f" Tickers exclus ({len(excluded_tickers)}) : {excluded_tickers}")

    return filtered_prices, excluded_tickers


# Selection of interactive dates
st.subheader("Construction of the price index")

start_date = st.date_input("Start date", value=pd.to_datetime("2010-04-01"), key="start_date")
end_date = st.date_input("End date", value=pd.to_datetime("2018-12-28"), key="end_date")


# Application of the function for SPX
spx_energy_prices, spx_excluded = filter_prices(spx_prices, spx_tickers, start_date, end_date)
sxxp_energy_prices, sxxp_excluded = filter_prices(sxxp_prices, sxxp_tickers, start_date, end_date)

# Display results for SPX
st.subheader("Filtered prices for SPX")
with st.expander("Show excluded columns for SPX"):
    st.write("**Columns excluded for SPX:**", spx_excluded)
with st.expander("Show filtered prices for SPX"):
    st.dataframe(spx_energy_prices)

# Display results for SXXP
st.subheader("Filtered prices for SXXP")
with st.expander("Show excluded columns for SXXP"):
    st.write("**Columns excluded for SXXP:**", sxxp_excluded)
with st.expander("Show filtered prices for SXXP"):
    st.dataframe(sxxp_energy_prices)


# Function to convert SXXP prices into dollars
def convert_usd(index_prices, forex_data):
    """Converts SXXP prices into dollars using the EUR/USD exchange rate corresponding to each date."""
    # Formatting dates
    index_prices["Dates"] = pd.to_datetime(index_prices["Dates"])
    forex_data["Dates"] = pd.to_datetime(forex_data["Dates"])

    # Fusion left on dates
    merged_data = pd.merge(index_prices, forex_data[["Dates", "EURUSD"]], on="Dates", how="left")

    # Verification of missing exchange rates
    if merged_data["EURUSD"].isna().any():
        st.warning("Certaines dates n'ont pas de taux de change correspondant.")

    # Price conversion
    numeric_cols = merged_data.select_dtypes(include="number").columns.drop("EURUSD")
    for col in numeric_cols:
        merged_data[col] = merged_data[col] * merged_data["EURUSD"]

    # Deleted EURUSD column
    merged_data.drop(columns=["EURUSD"], inplace=True)

    return merged_data


# Function to merge SPX and SXXP prices


# Conversion of SXXP prices into dollars
st.subheader("Conversion of SXXP prices into dollars")
forex_data = donnees["forex_data"]
sxxp_energy_prices_usd = convert_usd(sxxp_energy_prices, forex_data)
st.write("**SXXP price converted into dollars:**")
st.dataframe(sxxp_energy_prices_usd)

# Merging data to create index
st.subheader("Merger of SPX and SXXP prices for the index")
index_energy_prices = merge_dates(spx_energy_prices, sxxp_energy_prices_usd)
st.write(f"**Aligned prices for index '{secteur_choisi}' :**")
st.dataframe(index_energy_prices)

st.subheader("Price conversion into other currencies")
st.write(
    "European closing prices are converted to US dollars at the exchange rate for each observation."
)


# Function to convert prices into dollars in another currency
def convert_usd_currency(prices_df, forex_data):
    """Converts prices into dollars into a chosen currency.
    prices_df: DataFrame containing prices, with a first column 'Dates' and the following columns for prices in USD."""
    prices_df["Dates"] = pd.to_datetime(prices_df["Dates"])
    forex_data["Dates"] = pd.to_datetime(forex_data["Dates"])

    # Dictionary of currencies and their exchange rate columns
    currency_options = {
        "GBP": "USDGBP",
        "JPY": "USDJPY",
        "CNY": "USDCNY",
        "CAD": "USDCAD",
        "EUR": "EURUSD",
    }

    def convert(target_currency):
        """Sub-function to perform conversion according to the selected currency."""
        if target_currency not in currency_options:
            raise ValueError(
                f"Target currency '{target_currency}' is unavailable. Choose from {list(currency_options.keys())}."
            )

        rate_column = currency_options[target_currency]

        # Verification of exchange rate availability
        if rate_column not in forex_data.columns:
            raise ValueError(f"La colonne '{rate_column}' est absente de forex_data.")

        # Merger with exchange rates
        merged_data = pd.merge(
            prices_df, forex_data[["Dates", rate_column]], on="Dates", how="left"
        )

        # Verification of missing data
        if merged_data[rate_column].isna().any():
            st.warning(f"Certaines dates n'ont pas de taux de change pour '{rate_column}'.")

        # Price conversion
        for col in merged_data.columns[1:-1]:  # Exclure 'Dates' et 'rate_column'
            if target_currency == "EUR":  # Conversion USD -> EUR
                merged_data[col] = merged_data[col] / merged_data[rate_column]
            else:  # Conversion USD -> Autres devises
                merged_data[col] = merged_data[col] * merged_data[rate_column]

        # Abolition of the exchange rate column
        merged_data.drop(columns=[rate_column], inplace=True)

        return merged_data

    # Liste interactive
    target_currency = st.selectbox("Select a target currency:", list(currency_options.keys()))
    converted_df = convert(target_currency)
    st.write(f"**Converted to : {target_currency}**")
    st.dataframe(converted_df)

    return converted_df


# Application of conversion
forex_data = donnees["forex_data"]
converted_prices = convert_usd_currency(index_energy_prices, forex_data)

# Explanation for standardization
st.subheader("Standardization of prices")
st.write(
    "Each component starts at its first available price. This lets stocks with different price levels enter the same index."
)

# Function to normalize prices


# Application of standardization
normalized_prices = normalize_prices(index_energy_prices)
st.write("**Standard data:**")
st.dataframe(normalized_prices)

# Explanation of weighting
st.subheader("Calculation of market capitalization weights")
st.write("Match each constituent with its market capitalisation to determine its starting weight.")

# Function to calculate weights


# Application of the function for weights
qualitativ_2018 = donnees["qualitativ_2018"]
qualitativ_2019 = donnees["qualitativ_2019"]
marketcap_weights = market_cap_weights(index_energy_prices, qualitativ_2018)
st.write("**Ponderations based on market capitalization:**")
st.dataframe(marketcap_weights)

# Explanation of index construction
st.subheader(" Construction de l'indice sectoriel")
st.write(
    "Combine the normalised component prices using the selected weights. All index levels start at 100."
)

# Application of the function to build the index
index_energy = construct_index(index_energy_prices, marketcap_weights)
st.write(f"**Sector index {secteur_choisi.lower()} construit :**")
st.dataframe(index_energy)

# Loading the necessary data
index_data = donnees["index_data"]  # Feuille "Index"
forex_data = donnees["forex_data"]  # Feuille "Forex"

# Function to prepare benchmarks

# Prepare benchmarks
spx_index = prepare_reference_index(index_data, "SPX Index")  # Benchmark SPX
sxxp_index = prepare_reference_index(index_data, "SXXP Index")  # Benchmark SXXP

# Converts and normalizes benchmark SXXP to USD
sxxp_index_usd = convert_usd(sxxp_index, forex_data)  # Conversion en USD

# Merge Benchmarks with Sector Index
index_with_benchmarks = pd.merge(
    index_energy, spx_index, on="Dates", how="inner", suffixes=("", "_SPX")
)
index_with_benchmarks = pd.merge(
    index_with_benchmarks, sxxp_index_usd, on="Dates", how="inner", suffixes=("", "_SXXP")
)

# Function to adjust first value to 100


# Adjusts index and benchmark columns
columns_to_adjust = ["Index_Value", "Index_Value_SPX", "Index_Value_SXXP"]
index_with_benchmarks = adjust_to_base_100(index_with_benchmarks, columns_to_adjust)

# Visualisation
st.subheader(f" Sector index '{secteur_choisi.lower()}' avec Benchmarks")
fig, ax = plt.subplots(figsize=(12, 6))

# Trace l'indice sectoriel
ax.plot(
    index_with_benchmarks["Dates"],
    index_with_benchmarks["Index_Value"],
    label=f"Sector index '{secteur_choisi}'",
    linewidth=2,
    color="blue",
)

# Trace the SPX benchmark
ax.plot(
    index_with_benchmarks["Dates"],
    index_with_benchmarks["Index_Value_SPX"],
    label="Benchmark SPX",
    linestyle="--",
    color="orange",
)

# Draw the benchmark SXXP
ax.plot(
    index_with_benchmarks["Dates"],
    index_with_benchmarks["Index_Value_SXXP"],
    label="Benchmark SXXP (en USD)",
    linestyle=":",
    color="green",
)

# Graphic Configurations
ax.set_title(f"Sector index '{secteur_choisi}' with benchmarks (base 100)", fontsize=16)
ax.set_xlabel("Dates", fontsize=12)
ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
ax.legend(fontsize=12)
ax.grid(True, linestyle="--", alpha=0.6)

# Automatic backup in the temporary directory
save_figure(fig, f"indice_sectoriel_{secteur_choisi.lower().replace(' ', '_')}_avec_benchmark.png")

# Show graph
st.pyplot(fig)


# Function to build an index by country
def construct_index_pays(prices, weights, qualitativ_data):
    """Builds a sectoral index based on selected countries in an interactive interface."""
    ticker_column = weights.columns[0]

    # List of country options
    country_options = ["All"] + qualitativ_data["COUNTRY"].dropna().unique().tolist()

    # Interactive multi-country selection
    selected_countries = st.multiselect(
        "Select countries to filter the index:", options=country_options, default=["All"]
    )

    # Country filtering
    if "All" in selected_countries:
        filtered_weights = weights
    else:
        ticker_countries = qualitativ_data[[qualitativ_data.columns[0], "COUNTRY"]]
        filtered_weights = pd.merge(
            weights,
            ticker_countries,
            left_on=ticker_column,
            right_on=qualitativ_data.columns[0],
            how="inner",
        )
        filtered_weights = filtered_weights[filtered_weights["COUNTRY"].isin(selected_countries)]

    # Verification of data after filtering
    if filtered_weights.empty:
        st.warning("No tickers match the selected countries.")
        return pd.DataFrame({"Dates": [], "Index_Value": []})  # DataFrame vide

    # Merger of weights with prices
    merged_data = pd.melt(prices, id_vars=["Dates"], var_name="Ticker", value_name="Price")
    merged_data = pd.merge(
        merged_data, filtered_weights, left_on="Ticker", right_on=ticker_column, how="inner"
    )

    # Calculation of weighted prices
    merged_data["Weighted_Price"] = merged_data["Price"] * merged_data[weights.columns[1]]

    # Calculation of the weighted sum for each date
    index = merged_data.groupby("Dates")["Weighted_Price"].sum().reset_index()

    # Renommer et normaliser l'indice
    index.rename(columns={"Weighted_Price": "Index_Value"}, inplace=True)
    index["Index_Value"] = (index["Index_Value"] / index["Index_Value"].iloc[0]) * 100

    return index, selected_countries


# Function application
st.subheader("Construction of a sectoral index by country")
st.write("Choose a country subset to inspect how geography changes the sector exposure.")

# Interactive application of country selection
index_energy_pays, selected_countries = construct_index_pays(
    index_energy_prices, marketcap_weights, qualitativ_2018
)

# Displaying the resulting DataFrame
if not index_energy_pays.empty:
    st.write("**Country-filtered sectoral index:**")
    st.dataframe(index_energy_pays)

    # Readjusted SPX and SXXP benchmarks to start exactly at 100
    spx_index_normalized = adjust_to_base_100(spx_index, ["Index_Value"])
    sxxp_index_usd_normalized = adjust_to_base_100(sxxp_index_usd, ["Index_Value"])

    # Merge standardized benchmarks with sectoral index by country
    index_with_benchmarks_pays = pd.merge(
        index_energy_pays, spx_index_normalized, on="Dates", how="inner", suffixes=("", "_SPX")
    )
    index_with_benchmarks_pays = pd.merge(
        index_with_benchmarks_pays,
        sxxp_index_usd_normalized,
        on="Dates",
        how="inner",
        suffixes=("", "_SXXP"),
    )

    # Readjustment of sectoral index by country to start at 100
    index_with_benchmarks_pays = adjust_to_base_100(
        index_with_benchmarks_pays, ["Index_Value", "Index_Value_SPX", "Index_Value_SXXP"]
    )

    # Visualisation
    st.subheader(f" Sector index '{secteur_choisi}' by country avec Benchmarks")
    fig, ax = plt.subplots(figsize=(12, 6))

    # Trace the sectoral index by country
    ax.plot(
        index_with_benchmarks_pays["Dates"],
        index_with_benchmarks_pays["Index_Value"],
        label=f"Sector index '{secteur_choisi}' by country",
        linewidth=2,
        color="blue",
    )

    # Trace the SPX benchmark
    ax.plot(
        index_with_benchmarks_pays["Dates"],
        index_with_benchmarks_pays["Index_Value_SPX"],
        label="Benchmark SPX",
        linestyle="--",
        color="orange",
    )

    # Draw the benchmark SXXP
    ax.plot(
        index_with_benchmarks_pays["Dates"],
        index_with_benchmarks_pays["Index_Value_SXXP"],
        label="Benchmark SXXP (en USD)",
        linestyle=":",
        color="green",
    )

    # Graphic Configurations
    ax.set_title(
        f"Sector index '{secteur_choisi}' by country with benchmarks (base 100)", fontsize=16
    )
    ax.set_xlabel("Dates", fontsize=12)
    ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)

    save_figure(
        fig,
        f"indice_sectoriel_{secteur_choisi.lower().replace(' ', '_')}_par_pays_avec_benchmarks.png",
    )

    # Show graph
    st.pyplot(fig)
else:
    st.warning("The sectoral index per country is empty. Please check the selections.")


# Load the data
index_data = donnees["index_data"]  # Loading from the "Index" sheet

# Prepare SPX and SXXP indices
spx_index = prepare_reference_index(index_data, "SPX Index", base_100=True)
sxxp_index = prepare_reference_index(index_data, "SXXP Index", base_100=True)

# Interactive selection of the benchmark
st.subheader("Calculate the statistics of a sectoral index")
risk_free_rate = (
    st.number_input("Risk-free rate (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.1) / 100
)
use_reference = st.checkbox("Use an Alpha benchmark?", value=False)

reference_index = None
if use_reference:
    st.markdown("**Select a reference index** (SPX or SXXP) for the Alpha calculation:")
    selected_reference = st.selectbox("Reference index:", options=["SPX", "SXXP"], index=0)
    if selected_reference == "SPX":
        reference_index = spx_index
    elif selected_reference == "SXXP":
        reference_index = sxxp_index


# Function for calculating the main statistics
def stats_index(index, reference_index=None, risk_free_rate=0.0):
    """Calculates and displays the main statistics of an index.
    Args:
    index (pd.DataFrame): Target index data (with 'Dates' and 'Index_Value' columns).
    reference_index (pd.DataFrame, optional): Reference index data (with 'Dates' and 'Index_Value' columns).
    risk_free_rate (float, optional): Risk-free rate for calculating Alpha and Sharpe ratio.
    Returns:
    tuple: (stats_df, alpha, beta, merged_data) :
    - stats_df : Summary of index statistics
    - alpha : Valeur de l'Alpha (float)
    - beta: Beta value (float)
    - merged_data : merged data of target indices and reference"""
    if index is None or index.empty:
        st.error("The index data are empty or invalid.")
        return None, None, None, None

    required_columns = ["Dates", "Index_Value"]
    if not all(col in index.columns for col in required_columns):
        st.error(f"L'indice doit contenir les colonnes suivantes : {required_columns}")
        return None, None, None, None

    try:
        # Calculs de base
        start_value = index["Index_Value"].iloc[0]
        end_value = index["Index_Value"].iloc[-1]
        total_return = ((end_value - start_value) / start_value) * 100
        annualized_return = (end_value / start_value) ** (1 / (len(index) / 252)) - 1
        volatility = index["Index_Value"].pct_change().std() * (252**0.5)

        # Max Drawdown
        cumulative_returns = (1 + index["Index_Value"].pct_change()).cumprod()
        rolling_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        # Ratio de Sharpe
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility

        # Alpha and Beta (if a reference is provided)
        alpha = None
        beta = None
        merged = None
        if reference_index is not None:
            merged = pd.merge(
                index[["Dates", "Index_Value"]],
                reference_index[["Dates", "Index_Value"]],
                on="Dates",
                suffixes=("_target", "_reference"),
            )
            if not merged.empty:
                target_return = merged["Index_Value_target"].pct_change()
                reference_return = merged["Index_Value_reference"].pct_change()
                beta = np.cov(target_return.dropna(), reference_return.dropna())[0, 1] / np.var(
                    reference_return.dropna()
                )
                alpha = annualized_return - (
                    risk_free_rate + beta * (reference_return.mean() - risk_free_rate)
                )

        # Summary of statistics
        stats_data = {
            "Valeur Initiale": [start_value],
            "Valeur Finale": [end_value],
            "Rendement Total (%)": [total_return],
            "Rendement Annualisé (%)": [annualized_return * 100],
            "Volatilité Annualisée (%)": [volatility * 100],
            "Max Drawdown (%)": [max_drawdown],
            "Ratio de Sharpe": [sharpe_ratio],
        }
        if alpha is not None and beta is not None:
            stats_data["Alpha"] = [alpha]
            stats_data["Beta"] = [beta]

        st.write("**Indice Statistics Summary:**")
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df)

        return stats_df, alpha, beta, merged

    except Exception as e:
        st.error(f"Erreur lors du calcul des statistiques : {e}")
        return None, None, None, None


# Function for analysing main statistics and Alphas/betas
def analyze_statistics_and_alpha(
    stats_df, filename, merged_data=None, alpha_value=None, beta_value=None
):
    """Analyses the main statistics and, if available, Alphas and Betas.
    Args:
    stats_df (pd.DataFrame): DataFrame containing the main statistics calculated for the index.
    filename (str): File path to save statistics as an image.
    merged_data (pd.DataFrame, optional): merged data for Alpha/Beta analysis.
    alpha_value (float, optional): Alpha value calculated.
    beta_value (float, optional): calculated Beta value."""
    st.subheader("Complete Analysis of Index Statistics")

    # Analysis of main statistics
    if stats_df is not None and not stats_df.empty:
        # Extraction of values
        total_return = stats_df.at[0, "Rendement Total (%)"]
        annualized_return = stats_df.at[0, "Rendement Annualisé (%)"]
        volatility = stats_df.at[0, "Volatilité Annualisée (%)"]
        max_drawdown = stats_df.at[0, "Max Drawdown (%)"]
        sharpe_ratio = stats_df.at[0, "Ratio de Sharpe"]

        # Save statistics to a PNG file
        dataframe_to_image(stats_df, filename)

        # Conclusions based on statistics
        st.subheader("Conclusions based on Statistics")
        st.write(
            " **Rendement Total élevé :** L'indice a généré plus du double de son capital initial."
            if total_return > 100
            else " **Rendement Total faible :** L'indice a généré des gains limités."
        )
        st.write(
            " **Volatilité élevée :** L'indice est sujet à des fluctuations importantes."
            if volatility > 20
            else " **Volatilité modérée :** L'indice montre un bon équilibre entre stabilité et performance."
        )
        st.write(
            " **Max Drawdown élevé :** L'indice a subi une perte significative par rapport à son pic."
            if max_drawdown < -30
            else " **Max Drawdown faible :** L'indice est resté relativement stable."
        )
        st.write(
            " **Ratio de Sharpe satisfaisant :** L'indice offre un bon équilibre entre risque et rendement."
            if sharpe_ratio > 1
            else " **Ratio de Sharpe modéré :** Les rendements compensent tout juste le risque pris."
            if 0.5 <= sharpe_ratio <= 1
            else " **Ratio de Sharpe faible :** Les rendements ne compensent pas suffisamment le risque."
        )

    else:
        st.error("The main statistics are unavailable.")

    # Alphas and Beta analysis
    if isinstance(merged_data, pd.DataFrame) and not merged_data.empty:
        required_columns = ["Index_Value_target", "Index_Value_reference"]
        if all(col in merged_data.columns for col in required_columns):
            # Calculs journaliers
            merged_data["Daily_Return_Target"] = merged_data["Index_Value_target"].pct_change()
            merged_data["Daily_Return_Reference"] = merged_data[
                "Index_Value_reference"
            ].pct_change()

            # Displaying descriptive statistics
            st.subheader("Alphas and Beta analysis")

            if alpha_value is not None:
                st.write(f"**Alpha :** {alpha_value / 100:.4f}")
            else:
                st.write("**Alpha:** Not calculated")

            if beta_value is not None:
                st.write(f"**Beta :** {beta_value:.4f}")
            else:
                st.write("**Beta:** Not calculated")

            # Conclusions based on Alpha
            if alpha_value is not None:
                st.write("Conclusion on Alpha:")
                if alpha_value > 0:
                    st.write(
                        "**Positive Alpha:** The target index overperforms the benchmark after adjusting for risk."
                    )
                elif alpha_value < 0:
                    st.write(
                        "**Alpha negative:** The target index underperforms the benchmark after adjustment for risk."
                    )
                else:
                    st.write(
                        "**Nil Alpha:** The target index has a performance equivalent to that of the reference index after adjustment for risk."
                    )
            else:
                st.warning("Alpha is not available for this analysis.")

            # Conclusions based on Beta
            if beta_value is not None:
                st.write("Conclusion on Beta:")
                if beta_value > 1:
                    st.write("**Beta > 1:** The target index is more volatile than the benchmark.")
                elif beta_value < 1:
                    st.write("**Beta < 1:** The target index is less volatile than the benchmark.")
                else:
                    st.write(
                        "**Beta 1 :** The target index closely follows the volatility of the benchmark."
                    )
            else:
                st.warning("Beta is not available for this analysis.")

            # Comparison of yields
            st.subheader("Comparison of Daily Performance")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(
                merged_data["Dates"],
                merged_data["Daily_Return_Target"],
                label="Rendements Cible",
                alpha=0.7,
            )
            ax.plot(
                merged_data["Dates"],
                merged_data["Daily_Return_Reference"],
                label="Performance Reference",
                alpha=0.7,
            )
            ax.set_title("Comparaison des Rendements Journaliers", fontsize=14)
            ax.set_xlabel("Dates", fontsize=12)
            ax.set_ylabel("Rendements (%)", fontsize=12)
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.legend(fontsize=12)
            st.pyplot(fig)
        else:
            st.warning(
                "The columns required for Alpha/Beta analysis are missing from the merged data."
            )
    else:
        st.warning("Data for Alpha/Beta analysis are unavailable.")


# Call for detailed analysis with full conclusion
if reference_index is not None:
    stats_df, alpha, beta, merged_data = stats_index(
        index_energy, reference_index=reference_index, risk_free_rate=risk_free_rate
    )
    if stats_df is not None:
        # Sets a single file to save statistics
        stats_filename_reference = (
            f"Statistiques_Indice_{secteur_choisi.lower().replace(' ', '_')}.png"
        )

        analyze_statistics_and_alpha(
            stats_df=stats_df,
            filename=stats_filename_reference,
            merged_data=merged_data,
            alpha_value=alpha * 100 if alpha is not None else None,
            beta_value=beta if beta is not None else None,
        )
    else:
        st.warning(
            "The main statistics or Alphas/Betas could not be calculated for the data provided."
        )
else:
    st.warning("No benchmark selected. Analysis of Alphas and Betas ignored.")

st.header("Sector index rebalancing")
st.write("Choose the final year and compare the rebalanced index with its initial holdings.")


# Function to process prices for a given year
def process_prices_year(spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, year):
    spx_prices["Dates"] = pd.to_datetime(spx_prices["Dates"])
    sxxp_prices["Dates"] = pd.to_datetime(sxxp_prices["Dates"])

    # Filter the data for the specified year
    spx_year_data = spx_prices[
        (spx_prices["Dates"] >= f"{year}-01-01") & (spx_prices["Dates"] <= f"{year}-12-31")
    ]
    sxxp_year_data = sxxp_prices[
        (sxxp_prices["Dates"] >= f"{year}-01-01") & (sxxp_prices["Dates"] <= f"{year}-12-31")
    ]

    # Determines common dates
    start_date = max(spx_year_data["Dates"].min(), sxxp_year_data["Dates"].min())
    end_date = min(spx_year_data["Dates"].max(), sxxp_year_data["Dates"].max())

    # Filter data and apply transformations
    spx_filtered, _ = filter_prices(spx_prices, spx_tickers, start_date, end_date)
    sxxp_filtered, _ = filter_prices(sxxp_prices, sxxp_tickers, start_date, end_date)
    sxxp_usd = convert_usd(sxxp_filtered, forex_data)
    combined_prices = merge_dates(spx_filtered, sxxp_usd)
    normalized_prices = normalize_prices(combined_prices)

    return normalized_prices


def rebalance_multiple_years(
    initial_index,
    end_year,
    spx_prices,
    sxxp_prices,
    spx_tickers,
    sxxp_tickers,
    forex_data,
    qualitativ_data_by_year,
):
    """Rebalances the sectoral index successively for all years up to the selected year.
    Args:
    - initial_index (pd.DataFrame): The initial index before rebalancing.
    - end_year (int): Selected year for rebalancing.
    - spx_prices, sxxp_prices (pd.DataFrame): Price data SPX and SXXP.
    - spx_tickers, sxxp_tickers (list): Markers of SPX and SXXP indices.
    - forex_data (pd.DataFrame): Forex data for currency conversion.
    -qualityiv_data_by_year (dict): Qualitative data per year.
    Returns:
    - pd.DataFrame: Sector index adjusted."""
    index = initial_index.copy()
    start_year = index["Dates"].iloc[-1].year + 1  # First year not yet balanced

    for year in range(start_year, end_year + 1):
        # Recover prices for the year
        prices_for_year = process_prices_year(
            spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, year
        )
        qualitativ_for_year = qualitativ_data_by_year.get(year)

        if prices_for_year.empty:
            # Pass the year if the data is missing
            continue

        # Apply the rebalance for the year
        index = rebalance_index(index, prices_for_year, qualitativ_for_year)

    return index


# Load qualitative data by year
qualitativ_data_by_year = {}
available_years = [2019, 2020]

for year in available_years:
    try:
        qualitativ_data_by_year[year] = donnees[f"qualitativ_{year}"]
    except KeyError:
        st.warning(f"Fundamentals for {year} are unavailable.")
        qualitativ_data_by_year[year] = None

# Interface Interactive
st.subheader(" Rebalancement Dynamique de l'Indice")
selected_year = st.selectbox(
    "Choose a year for the adjustment:",
    options=range(2010, 2021),  # Available year range
    index=10,  # Default: 2020
)

# Adjustment for the selected year
st.subheader(f" Index rebalancing through {selected_year}")

# Verifies the necessary qualitative data
if any(
    qualitativ_data_by_year[year] is None
    for year in range(2010, selected_year + 1)
    if year in available_years
):
    st.error("Some of the qualitative data required for rebalancing are not available.")
else:
    # Apply multiple balancing
    index_energy_rebalanced = rebalance_multiple_years(
        index_energy,
        selected_year,
        spx_prices,
        sxxp_prices,
        spx_tickers,
        sxxp_tickers,
        forex_data,
        qualitativ_data_by_year,
    )

    # Visualisation
    st.subheader(
        f" Évolution de l'Sector index '{secteur_choisi}' after rebalancing ({selected_year})"
    )
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        index_energy_rebalanced["Dates"],
        index_energy_rebalanced["Index_Value"],
        label=f"Sector index '{secteur_choisi}' Rebalanced",
        color="purple",
        linewidth=2,
    )
    ax.set_title(
        f"Évolution de l'Sector index '{secteur_choisi}' for ({selected_year})", fontsize=16
    )
    ax.set_xlabel("Dates", fontsize=12)
    ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    st.pyplot(fig)

    # Recording the chart
    filename = f"indice_sectoriel_{secteur_choisi.replace(' ', '_').lower()}_rebalancement_{selected_year}.png"
    save_figure(fig, filename)


st.header("Financial-strength index")

st.write(
    "The financial-strength screen combines four fundamental measures. Set their weights before ranking the universe."
)

# Objectif de l'analyse
st.subheader(" Objectif")
st.write(
    "A high score can come from several combinations of fundamentals. Inspect the inputs for the companies selected."
)

# Methodology and Formulas
st.subheader("Methodology and Formulas")


# Function to calculate scores and display results
def calcul_score(qualitativ_data, px_to_book, pe_ratio, cur_mkcap, eqy_dvd):
    """Calculates the fundamentals score for each company on the "qualitativ_data" sheet.
    Excludes companies with missing criteria and shows how many enterprises are excluded.
    Arguments :
    qualityiv_data: DataFrame containing basic data (PX_TO_BOOK, PE_RATIO, etc.).
    px_to_book, pe_ratio, cur_mkcap, eqy_dvd : Values between 0 and 1 to weigh the score as we please.
    Retour :
    DataFrame containing the tickers and their scores, showing exclusions in Streamlit."""

    # Rename columns to match expectations
    qualitativ_data.rename(
        columns={
            "PX_TO_BOOK": "PX_TO_BOOK_RATIO",
            "EQY_DVD_YLD": "EQY_DVD_YLD_IND",
            "Ticker": "Ticker",
        },
        inplace=True,
    )

    # Replace commas with dots and convert to digital
    cols_to_convert = ["PX_TO_BOOK_RATIO", "PE_RATIO", "CUR_MKT_CAP", "EQY_DVD_YLD_IND"]
    for col in cols_to_convert:
        qualitativ_data[col] = (
            qualitativ_data[col].replace(",", ".", regex=True).replace("#N/A N/A", None)
        )
        qualitativ_data[col] = pd.to_numeric(qualitativ_data[col], errors="coerce")

    # Verification and filtering of missing columns
    columns = ["Ticker", "PX_TO_BOOK_RATIO", "PE_RATIO", "CUR_MKT_CAP", "EQY_DVD_YLD_IND"]
    filtered_data = qualitativ_data.dropna(subset=columns).copy()
    excluded_count = len(qualitativ_data) - len(filtered_data)
    st.write(f" **Companies excluded for missing inputs :** {excluded_count}")

    # Calculation of standards for each criterion
    filtered_data["Norm_PX_TO_BOOK"] = (
        filtered_data["PX_TO_BOOK_RATIO"] - filtered_data["PX_TO_BOOK_RATIO"].min()
    ) / (filtered_data["PX_TO_BOOK_RATIO"].max() - filtered_data["PX_TO_BOOK_RATIO"].min())

    filtered_data["Norm_PE_RATIO_Inv"] = (
        1 / filtered_data["PE_RATIO"] - (1 / filtered_data["PE_RATIO"]).min()
    ) / ((1 / filtered_data["PE_RATIO"]).max() - (1 / filtered_data["PE_RATIO"]).min())

    filtered_data["Norm_CUR_MKT_CAP"] = (
        filtered_data["CUR_MKT_CAP"] - filtered_data["CUR_MKT_CAP"].min()
    ) / (filtered_data["CUR_MKT_CAP"].max() - filtered_data["CUR_MKT_CAP"].min())

    filtered_data["Norm_EQY_DVD_YLD_IND"] = (
        filtered_data["EQY_DVD_YLD_IND"] - filtered_data["EQY_DVD_YLD_IND"].min()
    ) / (filtered_data["EQY_DVD_YLD_IND"].max() - filtered_data["EQY_DVD_YLD_IND"].min())

    # Calculation of scores
    filtered_data["Score"] = (
        px_to_book * filtered_data["Norm_PX_TO_BOOK"]
        + pe_ratio * filtered_data["Norm_PE_RATIO_Inv"]
        + cur_mkcap * filtered_data["Norm_CUR_MKT_CAP"]
        + eqy_dvd * filtered_data["Norm_EQY_DVD_YLD_IND"]
    )

    # Sort results
    result = filtered_data[["Ticker", "Score"]].sort_values(by="Score", ascending=False)

    # Display result
    st.write("**Computed scores for businesses:**")
    st.dataframe(result)

    return result


# Function to calculate weights


# Initialization of default weights
default_weights = {"PX_TO_BOOK": 0.25, "PE_RATIO": 0.25, "CUR_MKT_CAP": 0.30, "EQY_DVD_YLD": 0.20}

# Interactive section for weights
st.subheader("Define weights for calculating scores")

reset_clicked = st.button("Reset to default values")

if reset_clicked:
    px_to_book = default_weights["PX_TO_BOOK"]
    pe_ratio = default_weights["PE_RATIO"]
    cur_mkcap = default_weights["CUR_MKT_CAP"]
    eqy_dvd = default_weights["EQY_DVD_YLD"]
    st.success("Weights have been reset to default values.")
else:
    px_to_book = st.slider(
        "Weight for PX_TO_BOOK (Price-to-Book Ratio)",
        0.0,
        1.0,
        default_weights["PX_TO_BOOK"],
        step=0.01,
    )
    pe_ratio = st.slider(
        "Weight for PE_RATIO (Price-to-Earnings Ratio)",
        0.0,
        1.0,
        default_weights["PE_RATIO"],
        step=0.01,
    )
    cur_mkcap = st.slider(
        "Weight for CUR_MKT_CAP (Capitalization Bursary)",
        0.0,
        1.0,
        default_weights["CUR_MKT_CAP"],
        step=0.01,
    )
    eqy_dvd = st.slider(
        "Weight for EQY_DVD_YLD", 0.0, 1.0, default_weights["EQY_DVD_YLD"], step=0.01
    )

# Checking weights
total_weights = px_to_book + pe_ratio + cur_mkcap + eqy_dvd
if not np.isclose(total_weights, 1.0, rtol=0, atol=1e-9):
    st.error(f"Weights must sum to 1. Current sum : {total_weights:.2f}")
    st.stop()

# Calculation of scores
st.success(f"Weights sum to {total_weights:.2f}.")
score = calcul_score(donnees["qualitativ_2018"], px_to_book, pe_ratio, cur_mkcap, eqy_dvd)

# Interactive section for number of enterprises
st.subheader("Company selection parameters")
total_companies = len(score)
top_n = st.slider(
    "Number of enterprises to be selected (Top N)",
    min_value=10,
    max_value=total_companies,
    value=10,
    step=1,
)
if top_n == total_companies:
    st.write("All available companies will be included in the index.")
else:
    st.write(f"The screen selects the top {top_n} companies.")

# Calculation of weights for selected companies
weight_score = weights_scores(score, top_n=top_n)
st.write("**Weight of selected companies:**")
st.dataframe(weight_score)

st.header("Fundamental index rebalancing")

# Loading essential data
forex_data = donnees["forex_data"]
spx_prices = donnees["spx_prices"]
sxxp_prices = donnees["sxxp_prices"]

# Step 1: Filtering companies with all the basics available
st.subheader("Filtering valid businesses")

# Recovers the kickers with calculated scores
tickers_score = list(weight_score.iloc[:, 0])

# Interactive section to display or hide the selected tickers
with st.expander("Show selected tickers"):
    st.write("**Tickers selected:**")
    st.write(tickers_score)


# Step 2: Filter prices based on kickers and dates
st.subheader("Price filtering over a given period")
start_date = st.date_input("Select a start date:", value=pd.to_datetime("2010-04-01"))
end_date = st.date_input("Select an end date:", value=pd.to_datetime("2018-12-28"))

# Price filtering for SPX
spx_score_prices, spx_excluded = filter_prices(spx_prices, tickers_score, start_date, end_date)

with st.expander("Show excluded tickers for SPX"):
    st.write("**Excluded tickers for SPX:**", spx_excluded)

with st.expander("Show filtered prices for SPX"):
    st.write("** filtered prices for SPX:**")
    st.dataframe(spx_score_prices)

# Price filtering for SXXP
sxxp_score_prices, sxxp_excluded = filter_prices(sxxp_prices, tickers_score, start_date, end_date)
with st.expander("Show excluded tickers for SXXP"):
    st.write("**Excluded Tickers for SXXP:**", sxxp_excluded)

with st.expander("Show filtered prices for SXXP"):
    st.write("** filtered prices for SXXP:**")
    st.dataframe(sxxp_score_prices)


# Step 3: Conversion of SXXP prices into dollars
st.subheader("Conversion of SXXP prices into dollars")
sxxp_score_prices_usd = convert_usd(sxxp_score_prices, forex_data)
st.write("**Price converted into dollars:**")
st.dataframe(sxxp_score_prices_usd)

# Step 4: Fusion of SPX and SXXP prices
st.subheader("Merger of SPX and SXXP prices")
score_prices = merge_dates(spx_score_prices, sxxp_score_prices_usd)
st.write("**Consolidated prices:**")
st.dataframe(score_prices)

# Step 5: Standardization of prices
st.subheader("Standardization of prices")
score_prices_normalize = normalize_prices(score_prices)
st.write("**Standard prices:**")
st.dataframe(score_prices_normalize)

# Step 6: Construction of the index based on scores
st.subheader("Construction of index based on scores")
index_score = construct_index(score_prices_normalize, weight_score)
st.write("**Indice de style construit :**")
st.dataframe(index_score)

# Visualisation de l'indice avant rebalancement
st.subheader(" Visualisation de l'indice avant rebalancement")
fig_before, ax_before = plt.subplots(figsize=(10, 5))
ax_before.plot(
    index_score["Dates"],
    index_score["Index_Value"],
    label="Indice Avant Rebalancement",
    color="blue",
    linewidth=2,
)
ax_before.set_title("Indice Avant Rebalancement", fontsize=14)
ax_before.set_xlabel("Dates", fontsize=12)
ax_before.set_ylabel("Valeur de l'Indice", fontsize=12)
ax_before.legend(fontsize=12)
ax_before.grid(True, linestyle="--", alpha=0.6)

# Affichage
st.pyplot(fig_before)

# Recording the chart before rebalancing
filename_before = "indiceII_avant_rebalancement.png"
save_figure(fig_before, filename_before)

st.subheader("Analysis of index statistics before adjustment")
stats_df, alpha, beta, merged_data = stats_index(index_score)

if stats_df is not None:
    # Save statistics to a PNG file
    stats_filename_before = "Statistiques_IndiceII_Avant_Rebalancement.png"

    # Single call with all arguments
    analyze_statistics_and_alpha(
        stats_df=stats_df,
        filename=stats_filename_before,
        merged_data=merged_data,
        alpha_value=alpha,
        beta_value=beta,
    )
else:
    st.error("Could not calculate statistics before rebalancing.")

# Step 8: Dynamic Index Adjustment
st.subheader(f" Index rebalancing through {selected_year}")
if selected_year not in available_years:
    st.error(f"Données qualitatives indisponibles for {selected_year}. Select a different year.")
else:
    index_energy_rebalanced = rebalance_multiple_years(
        index_score,
        selected_year,
        spx_prices,
        sxxp_prices,
        tickers_score,
        tickers_score,
        forex_data,
        qualitativ_data_by_year,
    )
    st.write(f"**Index rebalanced through {selected_year} :**")

    # Visualisation of index after rebalancing
    st.subheader("Visualisation of index after rebalancing")
    fig_after, ax_after = plt.subplots(figsize=(10, 5))
    ax_after.plot(
        index_energy_rebalanced["Dates"],
        index_energy_rebalanced["Index_Value"],
        label="Index After Adjustment",
        color="green",
        linewidth=2,
    )
    ax_after.set_title("Indice Après Rebalancement", fontsize=14)
    ax_after.set_xlabel("Dates", fontsize=12)
    ax_after.set_ylabel("Valeur de l'Indice", fontsize=12)
    ax_after.legend(fontsize=12)
    ax_after.grid(True, linestyle="--", alpha=0.6)

    # Affichage
    st.pyplot(fig_after)
    # Recording the chart after balancing
filename_after = "indiceII_apres_rebalancement.png"
save_figure(fig_after, filename_after)
st.dataframe(index_energy_rebalanced)

# Step 9: Analysis of statistics after rebalancing
st.subheader("Analysis of index statistics after adjustment")
stats_df_rebalanced, alpha_rebalanced, beta_rebalanced, merged_data_rebalanced = stats_index(
    index_energy_rebalanced
)

if stats_df_rebalanced is not None:
    stats_filename_after = "Statistiques_IndiceII_Apres_Rebalancement.png"
    analyze_statistics_and_alpha(
        stats_df=stats_df_rebalanced,
        filename=stats_filename_after,
        merged_data=merged_data_rebalanced,
        alpha_value=alpha_rebalanced,
        beta_value=beta_rebalanced,
    )
else:
    st.error("Could not calculate statistics after rebalancing.")


# Function to rebalance the years available from 2019
def rebalance_available_years(
    initial_index,
    end_year,
    spx_prices,
    sxxp_prices,
    spx_tickers,
    sxxp_tickers,
    forex_data,
    qualitativ_data_by_year,
):
    """Rebalances the sectoral index successively for the available years, starting from 2019.
    Args:
    - initial_index (pd.DataFrame): The initial index before rebalancing.
    - end_year (int): Selected year for rebalancing.
    - spx_prices, sxxp_prices (pd.DataFrame): Price data SPX and SXXP.
    - spx_tickers, sxxp_tickers (list): Markers of SPX and SXXP indices.
    - forex_data (pd.DataFrame): Forex data for currency conversion.
    -qualityiv_data_by_year (dict): Qualitative data available per year.
    Returns:
    - pd.DataFrame: Sector index adjusted."""
    index = initial_index.copy()

    for year in sorted(qualitativ_data_by_year.keys()):
        if year < 2019:  # Ignore years before 2019
            continue
        if year > end_year:
            break  # Stop if we exceed the selected year

        qualitativ_for_year = qualitativ_data_by_year.get(year)
        if qualitativ_for_year is None:
            st.warning(f"Missing fundamentals for {year}.")
            continue

        # Process prices for the current year
        prices_for_year = process_prices_year(
            spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, year
        )
        if prices_for_year.empty:
            st.warning(f"No prices available for {year}.")
            continue

        # Apply the rebalance for the year
        index = rebalance_index(index, prices_for_year, qualitativ_for_year)

    return index


# Verification and application of rebalancing
if selected_year not in available_years:
    st.error(f"Données qualitatives indisponibles for {selected_year}. Select a different year.")
else:
    # Use index until end of 2018 as starting point
    index_energy_rebalanced = rebalance_available_years(
        index_score,
        selected_year,  # Use `index_score` as base, unchanged before 2019
        spx_prices,
        sxxp_prices,
        tickers_score,
        tickers_score,
        forex_data,
        qualitativ_data_by_year,
    )


# Section Momentum
st.header("Momentum index")
st.write(
    "The momentum study ranks stocks by historical performance and builds a basket from the selected leaders."
)


# Interactive parameters for the Momentum Index
momentum_period = st.number_input(
    "Timing period (in months):", min_value=1, max_value=24, value=6, key="momentum_period"
)
top_percent = st.slider(
    "Percentage of enterprises to be included in the index:",
    min_value=10,
    max_value=100,
    value=30,
    key="momentum_top_percent",
)
start_date = st.date_input(
    "Start date", value=pd.to_datetime("2010-04-01"), key="momentum_start_date"
)
end_date = st.date_input("End date", value=pd.to_datetime("2018-12-28"), key="momentum_end_date")

try:
    # Step 1: Apply filter_prices to all companies
    all_spx_tickers = spx_prices.columns[1:]  # All SPX tickers (excludes Dates column)
    all_sxxp_tickers = sxxp_prices.columns[1:]  # All SXXP tickers (excludes Dates column)

    spx_filtered, spx_excluded = filter_prices(spx_prices, all_spx_tickers, start_date, end_date)
    sxxp_filtered, sxxp_excluded = filter_prices(
        sxxp_prices, all_sxxp_tickers, start_date, end_date
    )

    if spx_filtered.empty or sxxp_filtered.empty:
        st.error("The filtered data for SPX or SXXP is empty. Check your dates or tickers.")
        st.stop()

    # Verification of duplicates in filtered DataFrams columns
    spx_filtered = spx_filtered.loc[:, ~spx_filtered.columns.duplicated()]
    sxxp_filtered = sxxp_filtered.loc[:, ~sxxp_filtered.columns.duplicated()]

    # Step 2: Conversion of SXXP prices into dollars
    sxxp_usd = convert_usd(sxxp_filtered, forex_data)

    # Verification of duplicates after conversion
    sxxp_usd = sxxp_usd.loc[:, ~sxxp_usd.columns.duplicated()]

    # Step 3: Merge SPX and SXXP prices
    combined_prices = merge_dates(spx_filtered, sxxp_usd)

    # Removal of duplicate columns in merged data
    if combined_prices.columns.duplicated().any():
        st.warning("Duplicated columns were detected and removed.")
        combined_prices = combined_prices.loc[:, ~combined_prices.columns.duplicated()]

    if combined_prices.empty:
        st.error("The combined data for SPX and SXXP are empty. Check your filters or input data.")
        st.stop()

    # Step 4: Standardization of prices
    normalized_prices = normalize_prices(combined_prices)

    # Verification of data after standardization
    st.write("**Data overview after processing and standardization:**")
    st.dataframe(normalized_prices.head())

    # Management of constant or duplicate columns
    constant_cols = normalized_prices.loc[:, (normalized_prices.nunique() <= 1)]
    if not constant_cols.empty:
        st.warning(f"Certaines colonnes sont constantes (ou vides) : {list(constant_cols.columns)}")
        normalized_prices = normalized_prices.drop(columns=constant_cols.columns)

    if normalized_prices.columns.duplicated().any():
        st.warning("Duplicated columns were detected and deleted in the standardized data.")
        normalized_prices = normalized_prices.loc[:, ~normalized_prices.columns.duplicated()]

    if normalized_prices.shape[1] <= 1:
        st.error("No valid column available after normalization. Check input data.")
        st.stop()

    # Step 5: Calculation of cumulative yields
    st.subheader("Calculation of cumulative yields")
    try:
        momentum_returns = normalized_prices.set_index("Dates").copy()

        if momentum_returns.empty:
            raise ValueError(
                "Les données normalisées sont vides. Impossible de calculer les rendements."
            )

        daily_returns = momentum_returns.pct_change().add(1)
        daily_returns = daily_returns.fillna(1)

        rolling_returns = daily_returns.rolling(window=momentum_period * 21, min_periods=1)
        momentum_cum_returns = rolling_returns.apply(np.prod, raw=True) - 1

        if momentum_cum_returns.isna().all(axis=None):
            raise ValueError(
                "Toutes les colonnes des rendements cumulés sont None. Vérifiez les données."
            )

        st.write("**Computed cumulative returns:**")
        st.dataframe(momentum_cum_returns.head())

    except Exception as e:
        st.error(f"Erreur : {e}")
        st.stop()

    # Step 6: Business Selection Momentum
    st.subheader("Selection of companies Momentum")
    if not momentum_cum_returns.empty:
        momentum_sorted = momentum_cum_returns.iloc[-1].sort_values(ascending=False)
        st.write("**Scores Momentum sorted:**")
        st.dataframe(momentum_sorted)

        top_n = int(len(momentum_sorted) * (top_percent / 100))
        if top_n <= 0:
            st.error("The percentage of companies selected is too low. Increase the percentage.")
            st.stop()

        selected_tickers = list(dict.fromkeys(momentum_sorted.head(top_n).index.tolist()))
        st.write(f"**Selected companies ({top_percent}% of the top performers) :**")
        st.write(selected_tickers)

        # Step 7: Calculation of Momentum Weights
        st.subheader("Calculation of the weights Momentum")

        if not momentum_sorted.empty:
            selected_scores = momentum_sorted.loc[selected_tickers]

            valid_tickers = list(set(selected_scores.index) & set(momentum_returns.columns))
            if not valid_tickers:
                st.error("No valid ticker found to build Momentum index.")
                st.stop()

            selected_scores = selected_scores.loc[valid_tickers]
            st.write(f" **Tickers passing the filter** : {len(valid_tickers)} companies.")
            st.dataframe(selected_scores)

            weighting_strategy = st.radio(
                "Weighting strategy",
                ("Pondération équivalente", "Pondération basée sur le score Momentum"),
                index=1,
            )

            weights = (
                pd.Series(1 / len(selected_scores), index=selected_scores.index)
                if weighting_strategy == "Pondération équivalente"
                else selected_scores / selected_scores.sum()
            )

            try:
                momentum_prices = momentum_returns[valid_tickers]
                momentum_index_values = (momentum_prices * weights.values).sum(axis=1)
                momentum_index = pd.DataFrame(
                    {
                        "Dates": momentum_prices.index,
                        "Index_Value": (momentum_index_values / momentum_index_values.iloc[0])
                        * 100,
                    }
                ).reset_index(drop=True)

                st.subheader("Momentum Index Visualization with Benchmarks")

                try:
                    index_data = donnees["index_data"]
                    forex_data = donnees["forex_data"]

                    spx_index = prepare_reference_index(index_data, "SPX Index", base_100=True)
                    sxxp_index = prepare_reference_index(index_data, "SXXP Index", base_100=True)
                    sxxp_index_usd = convert_usd(sxxp_index, forex_data)

                    index_with_benchmarks = pd.merge(
                        momentum_index, spx_index, on="Dates", how="inner", suffixes=("", "_SPX")
                    )
                    index_with_benchmarks = pd.merge(
                        index_with_benchmarks,
                        sxxp_index_usd,
                        on="Dates",
                        how="inner",
                        suffixes=("", "_SXXP"),
                    )

                    columns_to_adjust = ["Index_Value", "Index_Value_SPX", "Index_Value_SXXP"]
                    index_with_benchmarks = adjust_to_base_100(
                        index_with_benchmarks, columns_to_adjust
                    )

                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(
                        index_with_benchmarks["Dates"],
                        index_with_benchmarks["Index_Value"],
                        label="Indice Momentum",
                        linewidth=2,
                        color="blue",
                    )
                    ax.plot(
                        index_with_benchmarks["Dates"],
                        index_with_benchmarks["Index_Value_SPX"],
                        label="Benchmark SPX",
                        linestyle="--",
                        color="orange",
                    )
                    ax.plot(
                        index_with_benchmarks["Dates"],
                        index_with_benchmarks["Index_Value_SXXP"],
                        label="Benchmark SXXP (en USD)",
                        linestyle=":",
                        color="green",
                    )

                    ax.set_title("Indice Momentum with benchmarks (base 100)", fontsize=16)
                    ax.set_xlabel("Dates", fontsize=12)
                    ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
                    ax.legend(fontsize=12)
                    ax.grid(True, linestyle="--", alpha=0.6)

                    save_figure(fig, "Indice_Momentum_Avec_Benchmark.png")
                    st.pyplot(fig)

                except Exception as e:
                    st.error(f"Could not plot benchmark comparison : {e}")

            except Exception as e:
                st.error(f"Erreur lors de la construction de l'indice Momentum : {e}")

    else:
        st.error("Cumulative yields are empty. Cannot calculate Momentum weights.")

except Exception as e:
    st.error(f"Calculation error : {e}")
# Step 9: Analysis of Momentum Index Statistics
try:
    stats_df_momentum, alpha_momentum, beta_momentum, merged_data_momentum = stats_index(
        momentum_index
    )

    if stats_df_momentum is not None:
        st.write("The main statistics of the Momentum index have been calculated.")
    else:
        st.error("Could not calculate the statistics of the Momentum index.")

    # Step 10: In-depth Analysis of Statistics
    st.subheader("In-depth analysis of Momentum index statistics")
    analyze_statistics_and_alpha(
        stats_df=stats_df_momentum,
        filename="Statistiques_Indice_Momentum.png",
        merged_data=merged_data_momentum,
        alpha_value=alpha_momentum,
        beta_value=beta_momentum,
    )

except Exception as e:
    st.error(f"Erreur lors de l'analyse des statistiques : {e}")

st.header("Share results")
st.subheader("Preparation and pre-sending of the email")

# Variables for email
destinataire = st.text_input("Recipient's email address:", "recipient@example.com")
sujet = "Equity index analysis"
corps_message = (
    f"Sector: {secteur_choisi}\n"
    f"Subsectors: {', '.join(sous_secteurs_choisis) or 'All'}\n"
    f"Countries: {', '.join(selected_countries) or 'All'}\n\n"
    "The analysis covers sector, fundamental-strength and momentum indices. "
    "The downloadable archive contains the charts and statistics for the selected inputs."
)

mailto_link = f"mailto:{destinataire}?subject={urllib.parse.quote(sujet)}&body={urllib.parse.quote(corps_message)}"

if st.button(" Ouvrir l'application de messagerie"):
    st.markdown(f"[Open email draft]({mailto_link})", unsafe_allow_html=True)

if st.button("Download graphs and results"):
    zip_buffer = create_zip()
    zip_buffer.seek(0)

    st.download_button(
        label="Download results (.zip)",
        data=zip_buffer,
        file_name="analyse_financiere.zip",
        mime="application/zip",
    )
