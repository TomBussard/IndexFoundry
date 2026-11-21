# IndexFoundry

IndexFoundry makes the construction rules of an equity index visible. Start with US or European equities, choose a sector or investment style, then compare the resulting index with the S&P 500 or the STOXX Europe 600.

## Explore a construction rule

Filter the universe by sector or subsector, or build a momentum or financial-strength index. Compare its path with the reference benchmark, then inspect annualised return, volatility, Sharpe ratio and maximum drawdown. The app can export the analysis and charts.

## How much do the weights matter?

I ran the same three fictional price series through the application's index calculation. The equal-weight index ended at **108.00**. Giving the first company a 60 percent weight raised the final index to **112.60**. Both series start at 100. Run `python example.py` to repeat the calculation offline. [Example](example.py) · [Index calculation](index_math.py)

![Equal-weight and concentrated indices on the same three synthetic price series](figures/weighting-rules.png)

## Run locally

```sh
python -m pip install -r requirements.txt
python -m streamlit run Interactive_Financial_Index_Builder.py
```

The app reads `Data projet indices python.xlsx` in the working directory and attempts to download the original project workbook when it is absent. The workbook contains index levels, foreign exchange rates, constituent prices and fundamentals. [Index construction and data loading](Interactive_Financial_Index_Builder.py)

Portfolio by **Tom Bussard**.
