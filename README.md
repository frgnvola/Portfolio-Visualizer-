This tool uses Python, Flask, Pandas, and the YahooFinance API, alongside a CSV of the user's current asset portfolio to create a web dashboard to visualize assets with actionable insights, given current market trends and analyst predictions.

To use, begin by filling out the file portfolio.csv with your assets, including the asset type, ticker (if stock), shares, and cost basis. 

Run app.py, and connect to your localhost (typically an address like 127.0.0.1) to launch the dashboard.

Use the buttons in the top right corner to sort the portfolio by gains/loss, or decision type. Or, click on "Portfolio Insights & Decisions" to view recommended actions, based on the following:
- Unrealized gains
- Mitigating high losses
- Highly concentrated positions
- Analyst/Quant consensus (from yahoo finance data)
