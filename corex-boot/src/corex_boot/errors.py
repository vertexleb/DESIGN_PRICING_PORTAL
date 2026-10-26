"""Exception hierarchy. Every error carries a message fit to show a non-technical user."""


class CorexError(Exception):
    """Base class; str(exc) is shown to the user."""


class CancelledError(CorexError):
    def __init__(self, message: str = "Operation cancelled.") -> None:
        super().__init__(message)


class SourceError(CorexError):
    """The official download page could not be read or understood."""


class DownloadError(CorexError):
    pass


class ChecksumMismatchError(CorexError):
    pass


class InvalidIsoError(CorexError):
    pass


class DiskSafetyError(CorexError):
    """The selected disk is not (or is no longer) a safe target. Nothing was written."""


class DeviceDisconnectedError(CorexError):
    pass


class InsufficientCapacityError(CorexError):
    pass


class PermissionDeniedError(CorexError):
    pass


class UsbWriteError(CorexError):
    pass


class BootVerificationError(CorexError):
    pass


class PowerShellError(CorexError):
    pass
