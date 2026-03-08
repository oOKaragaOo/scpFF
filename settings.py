# ==================================================
# SCRAPER SETTINGS
# ==================================================

SCRAPER_SETTINGS = {
    # -------------------------
    # 1) PARSING FLOW
    # -------------------------
    "arrival_parser_enabled": True,
    "departure_parser_enabled": True,
    # False = skip popup detail click (time_range / distance / aircraft / etc.)
    "popup_scrape_enabled": False,
    # Missing-flight recovery after main parse loop.
    "recovery_enabled": False,
    # Switch back to arrival tab after departure pass.
    "auto_restore_tab": True,

    # -------------------------
    # 2) EXPORT (CSV)
    # -------------------------
    "export_enabled": True,
    "debug_export_enabled": False,
    "debug_week_export": False,
    # Recommended: "day" (used by current pipeline)
    # Alternatives exist but are less stable: week/month/year
    "export_mode": "day",

    # -------------------------
    # 3) CHART (POST-RUN)
    # -------------------------
    # If True, main.py will generate chart after scrape summary.
    "chart_export_enabled": True,
    # Threshold used by damage ratio: abs(departure - arrival) > threshold
    "chart_export_threshold": 60,
    # Split chart output into pages to avoid a huge single figure.
    "chart_export_charts_per_page": 12,
    # Pattern used by chart generator to load day CSV files.
    "chart_export_pattern": "export/day/**/flightsfrom_output/flightsfrom_*.csv",

    # -------------------------
    # 4) VALIDATION / REPORTING
    # -------------------------
    # Run read-only validator after append day export.
    "post_export_report_enabled": False,
    # Write expected rows metadata to flightsfrom_output/meta/*.json
    "validate_meta_export_enabled": False,

    # -------------------------
    # 5) RUNTIME / MAINTENANCE
    # -------------------------
    "restart_enabled": True,
    "restart_every_days": 1,
    # Safety gate for manual command: python main.py --cleanup-profiles
    "allow_profile_cleanup": True,
}
