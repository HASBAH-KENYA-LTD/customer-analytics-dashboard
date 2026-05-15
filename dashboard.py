"""
Customer Analytics Dashboard  ·  Multi-page  ·  Plotly Dash
Pages:
  /               Main overview    – all customers, KPIs, county charts
  /overlap        Overlap analysis – choropleth ward map (HFS / SUBD / both)
  /sales          Sales comparison – monthly trends, county breakdown
  /hotzones       Hot zone analysis – sales intensity choropleth + density map
  /boroughs       Borough (sublocation) choropleth
  /constituencies Constituency choropleth
  /coke           Coke vs HFS/SUBD customer map
"""

import warnings
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

from dash import Dash, dcc, html, Input, Output, clientside_callback, callback

import data                        # triggers all data loading + REP_CAT_COLORS population
import shp_data                    # triggers raw shapefile load for /shptest
import pages.main
import pages.overlap
import pages.sales
import pages.hotzones
import pages.boroughs
import pages.constituencies
import pages.coke
import pages.sublocations
import pages.shptest
import callbacks                   # __init__ imports all sub-modules, registering @callback decorators

from pages.main           import main_layout
from pages.overlap        import overlap_layout
from pages.sales          import sales_layout
from pages.hotzones       import hotzones_layout
from pages.boroughs       import boroughs_layout
from pages.constituencies import constituencies_layout
from pages.coke           import coke_layout
from pages.sublocations   import sublocations_layout
from pages.shptest        import shptest_layout

# ─────────────────────────────────────────────────────────────────────────────
# APP INSTANCE
# ─────────────────────────────────────────────────────────────────────────────
app = Dash(__name__, title="Customer Analytics · Kenya", suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div(
    id="root-container",
    style={"fontFamily":"'Segoe UI',Arial,sans-serif",
           "minHeight":"100vh","padding":"14px"},
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="theme-store", data="light"),
        html.Div(id="page-content"),
        # Floating dark-mode toggle — always on top of page content
        html.Button(
            id="theme-toggle", children="🌙",
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


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────────────────────
@callback(Output("page-content","children"), Input("url","pathname"))
def route(path):
    if path == "/overlap":
        return overlap_layout
    if path == "/sales":
        return sales_layout
    if path == "/hotzones":
        return hotzones_layout
    if path == "/boroughs":
        return boroughs_layout
    if path == "/constituencies":
        return constituencies_layout
    if path == "/coke":
        return coke_layout
    if path == "/sublocations":
        return sublocations_layout
    if path == "/shptest":
        return shptest_layout
    return main_layout


# ─────────────────────────────────────────────────────────────────────────────
# THEME TOGGLE
# ─────────────────────────────────────────────────────────────────────────────
from dash import State

@callback(
    Output("theme-store",  "data"),
    Output("theme-toggle", "children"),
    Input("theme-toggle",  "n_clicks"),
    State("theme-store",   "data"),
    prevent_initial_call=True,
)
def toggle_theme(_, current):
    if current == "light":
        return "dark", "☀️"
    return "light", "🌙"


# Apply / remove the dark-mode class on the root container via JS —
# avoids re-rendering any chart callbacks when the theme changes.
clientside_callback(
    """function(theme) {
        const el = document.getElementById('root-container');
        if (el) {
            if (theme === 'dark') el.classList.add('dark-mode');
            else                  el.classList.remove('dark-mode');
        }
        return window.dash_clientside.no_update;
    }""",
    Output("theme-store", "id"),   # dummy — store.id never changes
    Input("theme-store",  "data"),
)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
