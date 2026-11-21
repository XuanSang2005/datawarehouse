"""Lỗi nghiệp vụ dùng chung, được main.py chuyển thành HTTP response rõ ràng."""


class DataNotReadyError(Exception):
    """Dữ liệu cần thiết chưa có (vd bảng gold.ml_* chưa được script ML ghi). → HTTP 404.

    `hint` là câu lệnh/việc cần làm để có dữ liệu, hiển thị nguyên văn cho người dùng.
    """

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class InvalidParameterError(ValueError):
    """Tham số hợp lệ về kiểu nhưng sai về nghiệp vụ (vd date_from > date_to). → HTTP 422."""
