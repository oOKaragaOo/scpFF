# ==================================================
# SCRAPER SETTINGS
# ==================================================

SCRAPER_SETTINGS = {

    # =========================
    # PARSER
    # =========================
    "arrival_parser_enabled": True,
    "departure_parser_enabled": True,
    # when False the popup click/details extraction will be skipped
    # leaving related fields blank, other row data remains unchanged.
    "popup_scrape_enabled": True,

    # =========================
    # RECOVERY
    # =========================
    # missing-flight recovery (post-parse)
    "recovery_enabled": False,

    # =========================
    # TAB CONTROL
    # =========================
    "auto_restore_tab": True,

    # =========================
    # DEBUG
    # =========================
    "debug_week_export": False,

    # =========================
    # EXPORT
    # =========================
    "export_enabled": True,
    "debug_export_enabled": False,

    # export mode:
    # "day" 
    # >> Unstable ----> | "week" | "month" | "year" ----< Unstable <<
    "export_mode": "day",

    "restart_enabled": True,
    "restart_every_days": 1,

    # =========================
    # POST-EXPORT REPORT
    # =========================
    # when True run a read-only validator after each day export
    "post_export_report_enabled": False,
    "validate_meta_export_enabled": False,


    # =========================
    # PROFILE CLEANUP
    # =========================
    # Safety toggle for manual profile cleanup command.
    # When False, `python main.py --cleanup-profiles` will be blocked.
    "allow_profile_cleanup": True,

}
