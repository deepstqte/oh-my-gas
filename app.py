"""
Dash port of Shiny iris k-means example:

https://shiny.rstudio.com/gallery/kmeans-example.html
"""
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from datetime import datetime
import requests
import json
import plotly.express as px
import dash_table
import os

ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY", "GETANETHERSCANAPIKEYFROM_https://etherscan.io/apis"]
DEFAULT_ADDRESS = "0xD710B4cbF1A4E510F6c6e9245c5Cb65c4eB3Dc02"

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server

controls = dbc.Card(
    [
        dbc.FormGroup(
            [
                dbc.Label("Address"),
                dbc.Input(id="address", type="text", value=DEFAULT_ADDRESS),
            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label("Period"),
                dcc.RadioItems(
                    id="period",
                    options=[
                        {"label": col, "value": col} for col in ["Days", "Months"]
                    ],
                    value='Days'
                ),
            ]
        ),
    ],
    body=True,
)

app.layout = dbc.Container(
    [
        html.H1("Gas spend monitor"),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(controls, md=4),
                dbc.Col(dcc.Graph(id="spend-graph"), md=8),
            ],
            align="center",
        ),
        dbc.Row(
            [
                dbc.Col(html.Div(id="table"), md=11),
            ],
            align="center",
        ),
    ],
    fluid=True,
)


@app.callback(
    [
        Output("spend-graph", "figure"),
        Output("table", "children")
    ],
    [
        Input("period", "value"),
        Input("address", "value"),
    ],
)
def make_graph(period, address):
    address = address.lower()
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&apikey={ETHERSCAN_API_KEY}"
    all_txlist = requests.get(url).json()["result"]
    txlist = []
    for tx in all_txlist:
        if tx["from"] == address and int(tx["txreceipt_status"]) == 1:
            tx_date = datetime.fromtimestamp(int(tx["timeStamp"])).date()
            clean_tx = {
                "hash": tx["hash"],
                "year": tx_date.year,
                "month": str(tx_date.month) + "-" + str(tx_date.year),
                "day": str(tx_date.month) + "-" + str(tx_date.day) + "-" + str(tx_date.year),
                "to": tx["to"],
                "transaction_fee_eth": (float(tx["gasPrice"]) / 1000000000000000000) * float(tx["gasUsed"]),
                "gas_price_gwei": float(tx["gasPrice"]) / 1000000000,
            }
            txlist.append(clean_tx)
    df = pd.DataFrame(txlist)

    table_df = df.drop(["month", "year"], axis=1)
    table_df["hash"] = table_df["hash"].transform(lambda x: f"[ℹ️](https://etherscan.io/tx/{x})")
    table_df = table_df.rename(columns={
        "day": "Date",
        "to": "To",
        "hash": "",
        "transaction_fee_eth": "Fees paid in ETH",
        "gas_price_gwei": "Transaction gas price in Gwei",
    })

    table = dash_table.DataTable(
        columns=[{"name": i, "id": i, "presentation": "markdown"} for i in table_df.columns],
        data=table_df.to_dict('records'),
    )

    if period == "Days":
        df = df.groupby("day", as_index=False).agg({"transaction_fee_eth": "sum"})
        fig = px.bar(df, x="day", y='transaction_fee_eth')
    else:
        df = df.groupby("month", as_index=False).agg({"transaction_fee_eth": "sum"})
        fig = px.bar(df, x="month", y='transaction_fee_eth')

    return fig, table


if __name__ == "__main__":
    app.run_server(debug=True, port=8888)
