# IndexFoundry

IndexFoundry makes the construction rules of an equity index visible. Start with US or European equities, choose a sector or investment style, then compare the resulting index with the S&P 500 or the STOXX Europe 600.

## Explore a construction rule

Filter the universe by sector or subsector, or build a momentum or financial-strength index. Compare its path with the reference benchmark, then inspect annualised return, volatility, Sharpe ratio and maximum drawdown. The app can export the analysis and charts.

## Run locally

```sh
python -m pip install -r requirements.txt
python -m streamlit run Interactive_Financial_Index_Builder.py
```

The app reads `Data projet indices python.xlsx` in the working directory and attempts to download the original project workbook when it is absent. The workbook contains index levels, foreign exchange rates, constituent prices and fundamentals. [Index construction and data loading](Interactive_Financial_Index_Builder.py)
