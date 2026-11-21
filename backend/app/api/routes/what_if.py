from fastapi import APIRouter

from app.api.deps import DbConn
from app.schemas.what_if import WhatIfRequest, WhatIfResponse
from app.services import what_if_service

router = APIRouter(prefix="/what-if", tags=["what-if"])


@router.post("", response_model=WhatIfResponse)
def run_what_if(conn: DbConn, req: WhatIfRequest) -> WhatIfResponse:
    """Mô phỏng overbooking và chính sách đặt cọc theo rủi ro hủy (G4).

    Trả về doanh thu cứu được, số đêm có nguy cơ hết phòng, chi phí đền bù ước tính, lợi ích ròng,
    đường cong lợi ích theo mức overbooking và mức gợi ý. Công thức: docstring của
    `app/services/what_if_service.py`. Chỉ đọc dữ liệu, không ghi gì vào DB.
    """
    return what_if_service.run_what_if(conn, req)
