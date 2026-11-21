"""Shared business errors, turned into clear HTTP responses by main.py."""


class DataNotReadyError(Exception):
    """Required data is not available yet (e.g. gold.ml_* not written by the ML script). → HTTP 404.

    `hint` is the command/action needed to produce the data, shown verbatim to the user.
    """

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class InvalidParameterError(ValueError):
    """Parameter of a valid type but an invalid value (e.g. date_from > date_to). → HTTP 422."""
