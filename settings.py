# ==================================================
# SCRAPER SETTINGS
# ==================================================

SCRAPER_SETTINGS = {

    # =========================
    # PARSER
    # =========================
    "arrival_parser_enabled": True,
    "departure_parser_enabled": True,

    # =========================
    # RECOVERY
    # =========================
    # missing-flight recovery (post-parse)
    "recovery_enabled": True,

    # =========================
    # TAB CONTROL
    # =========================
    "auto_restore_tab": True,

    # =========================
    # DEBUG
    # =========================
    "debug_week_export": True,

    # =========================
    # EXPORT
    # =========================
    "export_enabled": True,
    "debug_export_enabled": True,

    # export mode:
    # "day" | "week" | "month" | "year"
    "export_mode": "year",

}
