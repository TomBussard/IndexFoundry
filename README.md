# IndexFoundry

IndexFoundry makes the construction rules of an equity index visible. Start with US or European equities, choose a sector or investment style, then compare the resulting index with the S&P 500 or the STOXX Europe 600.

## Explore a construction rule

Filter the universe by sector or subsector, or build a momentum or financial-strength index. Compare its path with the reference benchmark, then inspect annualised return, volatility, Sharpe ratio and maximum drawdown. The app can export the analysis and charts.

## How much do the weights matter?

I ran the same three fictional price series through the application's index calculation. The equal-weight index ended at **108.00**. Giving the first company a 60 percent weight raised the final index to **112.60**. Both series start at 100. Run `python example.py` to repeat the calculation offline. [Example](example.py) · [Index calculation](index_math.py)

![Equal-weight and concentrated indices on the same three synthetic price series](figures/weighting-rules.png)

## Read the last index level by hand

| Company | Start | Finish | Weight in the concentrated index |
| --- | ---: | ---: | ---: |
| Firm A | 100 | 120 | 60% |
| Firm B | 100 | 100 | 25% |
| Firm C | 100 | 104 | 15% |

An equal allocation earns the average of 20%, 0% and 4%, or 8%. The concentrated allocation earns 0.60 × 20% + 0.25 × 0% + 0.15 × 4% = 12.60%. The interactive example varies Firm A's starting weight and keeps the other two in a 5:3 ratio. Weights are joined to prices by ticker, so column ordering cannot change the result.

In the workbook workflow, I align the trading dates, convert European prices using the matching FX series, normalise prices, then compare the constructed index with its benchmark. The workbench also supports country subsets, financial-strength and momentum selections, rebalancing, and chart exports. Each session generates its own report archive.

[Weighting and rebasing](index_math.py) · [Workbook input contract](workbook.py) · [Sector and style studies](workbench.py) · [Report archive](reports.py)

## Run locally

```sh
python -m pip install -r requirements.txt
python -m streamlit run Interactive_Financial_Index_Builder.py
```

The opening **Weighting study** needs no workbook or network connection. For **Workbook analysis**, select a local eight-sheet Excel file or place `Data projet indices python.xlsx` in the working directory. The app reads it locally. [Required sheet names](workbook.py)

Tom Bussard
