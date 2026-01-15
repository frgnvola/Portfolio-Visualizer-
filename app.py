from flask import Flask, render_template, request
from portfolio_tool import load_and_process_portfolio, format_for_display

app = Flask(__name__)

# ------------------------------------------------------------
# COLOR FUNCTIONS FOR STYLER
# ------------------------------------------------------------

def color_pl(val):
    try:
        v = float(val)
        if v > 0:
            return "background-color:#d8ffd8;"      # green
        elif v < 0:
            return "background-color:#ffd8d8;"      # red
    except:
        pass
    return ""

def color_decision(val):
    if val == "Strong Buy":
        return "background-color:#b3e6ff;"
    if val == "Buy / Hold":
        return "background-color:#e6f7ff;"
    if val == "Review":
        return "background-color:#f0f0f0;"
    if val == "Trim":
        return "background-color:#ffe6b3;"
    if val == "Sell":
        return "background-color:#ffcccc;"
    return ""

# ------------------------------------------------------------
# MAIN ROUTE
# ------------------------------------------------------------

@app.route("/")
def index():

    df = load_and_process_portfolio()
    df = format_for_display(df)

    # Default load sorted by P/L dollar
    df = df.sort_values("pl_dollar", ascending=False)

    # Apply Styler
    styled = (
    df.style
      .map(color_pl, subset=["pl_dollar", "pl_pct"])
      .map(color_decision, subset=["decision"])
      .set_table_attributes('class="table table-striped table-bordered"')
)

    html_table = styled.to_html()

    # Fix pandas' broken table ID
    html_table = html_table.replace("<table ", "<table id=\"portfolioTable\" ")

    return render_template("index.html", table_html=html_table)

# ------------------------------------------------------------
# INSIGHTS ROUTE
# ------------------------------------------------------------

@app.route("/insights")
def insights():

    df = load_and_process_portfolio()

    trims = df[df["decision"].isin(["Trim", "Sell"])].sort_values("pl_dollar", ascending=False).head(5)
    buys  = df[df["decision"].isin(["Strong Buy", "Buy / Hold"])].sort_values("score", ascending=False).head(5)
    concentration = df.sort_values("weight_pct", ascending=False).head(5)
    movers = df.sort_values("pl_pct", ascending=False).head(5)

    return render_template(
        "insights.html",
        trims=trims.to_html(index=False, classes="table table-bordered"),
        buys=buys.to_html(index=False, classes="table table-bordered"),
        concentration=concentration.to_html(index=False, classes="table table-bordered"),
        movers=movers.to_html(index=False, classes="table table-bordered")
    )


# ------------------------------------------------------------
# FLASK START
# ------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)
