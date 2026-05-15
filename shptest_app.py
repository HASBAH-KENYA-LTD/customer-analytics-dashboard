"""
shptest_app.py — Standalone borough shapefile inspection app.

Serves ONLY the shapefile map — no links to other dashboard pages.
Any URL path shows the same map; there is no routing.

Dev:
    python shptest_app.py

Production (gunicorn):
    gunicorn shptest_app:server -w 1 -b 127.0.0.1:8051 --timeout 120 --access-logfile -
"""

import warnings
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

from dash import (
    Dash, html, dcc,
    Input, Output, State,
    callback, clientside_callback,
)

import data                 # loads customer data (needed for customer-dot overlay)
import shp_data             # loads borough shapefile
import callbacks.shptest    # registers all sht_* @callback decorators

from pages.shptest import shptest_body
from config import PRIMARY

app = Dash(
    __name__,
    title="Borough Map",
    suppress_callback_exceptions=True,
)
server = app.server   # WSGI entry point for gunicorn

app.layout = html.Div(
    id="root-container",
    className="dark-mode",   # default: dark
    style={"fontFamily": "'Segoe UI',Arial,sans-serif",
           "minHeight": "100vh", "padding": "14px"},
    children=[
        dcc.Store(id="theme-store", data="dark"),

        # ── Minimal branded header ────────────────────────────────────────────
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

        # ── Floating dark / light toggle ──────────────────────────────────────
        html.Button(
            id="theme-toggle",
            children="☀️",          # sun = currently dark, click for light
            title="Toggle dark / light mode",
            style={
                "position": "fixed", "bottom": "22px", "right": "22px",
                "zIndex": "9999", "fontSize": "20px",
                "padding": "6px 12px", "borderRadius": "50px",
                "border": "1px solid var(--border)",
                "background": "var(--card)", "color": "var(--text)",
                "cursor": "pointer",
                "boxShadow": "0 2px 8px rgba(0,0,0,.20)",
                "transition": "all 0.2s ease",
            },
        ),
    ],
)


@callback(
    Output("theme-store",  "data"),
    Output("theme-toggle", "children"),
    Input("theme-toggle",  "n_clicks"),
    State("theme-store",   "data"),
    prevent_initial_call=True,
)
def toggle_theme(_, current):
    if current == "dark":
        return "light", "🌙"
    return "dark", "☀️"


# Apply / remove dark-mode class via JS — avoids re-rendering chart callbacks
clientside_callback(
    """function(theme) {
        const el = document.getElementById('root-container');
        if (el) {
            if (theme === 'dark') el.classList.add('dark-mode');
            else                  el.classList.remove('dark-mode');
        }
        return window.dash_clientside.no_update;
    }""",
    Output("theme-store", "id"),   # dummy output — store.id never changes
    Input("theme-store",  "data"),
)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8051)
