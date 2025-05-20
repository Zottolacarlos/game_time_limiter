import os
from datetime import timedelta

if os.name == "nt":
    import win32serviceutil  # type: ignore
    import win32service  # type: ignore
    import win32event  # type: ignore

    from .monitor import Monitor, DEFAULT_LIMIT


    class GameTimeService(win32serviceutil.ServiceFramework):
        _svc_name_ = "GameTimeLimiter"
        _svc_display_name_ = "Game Time Limiter (Steam)"
        _svc_description_ = "Limita el tiempo diario de juego en Steam (daemon Python)."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.monitor = Monitor(DEFAULT_LIMIT)

        def SvcStop(self):  # noqa: N802
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):  # noqa: N802
            self.monitor.loop()