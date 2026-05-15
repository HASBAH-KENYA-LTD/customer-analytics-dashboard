"""
config.py — constants, colours, style dicts.
No local imports allowed here.
"""

MONTHS = [
    "December 2025",
    "January 2026", "February 2026", "March 2026", "April 2026",
]
MONTH_SHORT = ["Dec 25", "Jan 26", "Feb 26", "Mar 26", "Apr 26"]
TOTAL_COL   = "TOTAL "          # trailing space as in source file

CAT_COLORS = {"HFS": "#2980B9", "SUBD": "#E67E22"}
OVERLAP_COLORS = {
    "Both (Overlap)": "#8E44AD",
    "HFS Only":       "#2980B9",
    "SUBD Only":      "#E67E22",
    "No Customers":   "#D5D8DC",
}

# Qualitative palette for rep_category (populated after data load)
REP_CAT_PALETTE = [
    "#2980B9","#E74C3C","#27AE60","#F39C12","#8E44AD",
    "#16A085","#D35400","#2C3E50","#1ABC9C","#E91E63",
    "#607D8B","#795548","#FF5722","#9C27B0","#00BCD4",
    "#8BC34A","#FFC107","#FF9800","#3F51B5",
]
REP_CAT_COLORS: dict = {}   # filled by data.py after df is loaded

PRIMARY = "#1A3C6E"
BG      = "#F0F2F6"
CARD    = "#FFFFFF"
TEXT    = "#2C3E50"
MUTED   = "#7F8C8D"
BORDER  = "#DEE2E6"

CARD_S = {
    "background": "var(--card)", "borderRadius": "10px",
    "boxShadow": "0 1px 6px rgba(0,0,0,.09)", "padding": "14px",
}
LBL_S = {
    "fontSize": "10px", "fontWeight": "700", "color": "var(--muted)",
    "textTransform": "uppercase", "letterSpacing": "0.8px",
    "margin": "0 0 4px 0",
}
DROP_S = {"fontSize": "13px", "marginBottom": "10px"}

MAP_STYLE_OPTS = [
    {"label": "Street Map",  "value": "open-street-map"},
    {"label": "Light (Carto)","value": "carto-positron"},
    {"label": "Dark (Carto)", "value": "carto-darkmatter"},
    {"label": "Terrain",      "value": "stamen-terrain"},
    {"label": "Toner (B&W)",  "value": "stamen-toner"},
]
