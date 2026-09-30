"""In-app diagnostic: crash report from the native fault logs."""

from PyQt6.QtWidgets import QMessageBox


class CrashEvents:
    def crash_report(self):
        """Show the crash log summary (Help > Crash Report & Logs)."""
        from PyImageLabeling.controller.settings.CrashReportDialog import show
        show(self.view)