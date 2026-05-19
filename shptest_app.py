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

# ── Logging must be configured FIRST so all subsequent imports inherit it ─────
import logging_setup                                    # noqa: F401 (side-effects only)
from logging_setup import app_log, audit_log, error_log

import time
import traceback
from flask import request, g

from dash import (
    Dash, html, dcc,
    Input, Output, State,
    callback, clientside_callback,
)
from flask_compress import Compress

app_log.info("Starting shptest_app — importing data modules…")

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
server = app.server
Compress(server)      # gzip — reduces JS bundle transfer by ~70%


# ── Flask request hooks ───────────────────────────────────────────────────────

@server.before_request
def _before():
    g.t0 = time.perf_counter()


@server.after_request
def _after(response):
    ms  = (time.perf_counter() - g.t0) * 1000
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua  = request.headers.get("User-Agent", "-")[:80]
    audit_log.info(
        "%-16s %-4s %-40s %s  %dms  %s",
        ip, request.method, request.path,
        response.status_code, ms, ua,
    )
    if response.status_code >= 500:
        error_log.error(
            "5xx on %s %s → %s  (%.0f ms)",
            request.method, request.path, response.status_code, ms,
        )
    return response


@server.teardown_request
def _teardown(exc):
    if exc is not None:
        error_log.error(
            "Unhandled exception on %s %s\n%s",
            request.method, request.path,
            traceback.format_exc(),
        )


# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = html.Div(
    id="root-container",
    className="dark-mode",
    style={"fontFamily": "'Segoe UI',Arial,sans-serif",
           "minHeight": "100vh", "padding": "14px"},
    children=[
        dcc.Store(id="theme-store", data="dark"),

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

        html.Button(
            id="theme-toggle",
            children="☀️",
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


clientside_callback(
    """function(theme) {
        const el = document.getElementById('root-container');
        if (el) {
            if (theme === 'dark') el.classList.add('dark-mode');
            else                  el.classList.remove('dark-mode');
        }
        return window.dash_clientside.no_update;
    }""",
    Output("theme-store", "id"),
    Input("theme-store",  "data"),
)

app_log.info("shptest_app ready — layout built, callbacks registered")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8051)
