"""
shptest_app.py — Standalone borough shapefile inspection app.

Serves ONLY the shapefile map — no links to other dashboard pages.
Any URL path shows the same map; there is no routing.

Dev:
    python shptest_app.py

Production (gunicorn):
    gunicorn shptest_app:server -w 1 -b 0.0.0.0:8051 --timeout 120
"""

import warnings
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

from dash import Dash, html

import data            # loads customer data (needed for customer-dot overlay)
import shp_data        # loads borough shapefile
import callbacks.shptest   # registers all sht_* @callback decorators

from pages.shptest import shptest_body
from config import PRIMARY

app = Dash(
    __name__,
    title="Borough Map",
    suppress_callback_exceptions=True,
)
server = app.server   # expose WSGI entry point for gunicorn

app.layout = html.Div(
    id="root-container",
    style={"fontFamily": "'Segoe UI',Arial,sans-serif",
           "minHeight": "100vh", "padding": "14px"},
    children=[
        # Minimal branded header — no links to other pages
        html.Div(
            style={
                "display": "flex", "alignItems": "center",
                "marginBottom": "14px", "padding": "10px 14px",
                "borderRadius": "10px", "background": "var(--card)",
                "boxShadow": "0 1px 6px rgba(0,0,0,.09)",
            },
            children=[
                html.Span(
                    "Borough Shapefile Map",
                    style={"fontWeight": "700", "color": PRIMARY, "fontSize": "15px"},
                ),
            ],
        ),
        shptest_body,
    ],
)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8051)
