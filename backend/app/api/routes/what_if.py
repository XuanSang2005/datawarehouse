from fastapi import APIRouter

from app.api.deps import DbConn
from app.schemas.what_if import WhatIfRequest, WhatIfResponse
from app.services import what_if_service

router = APIRouter(prefix="/what-if", tags=["what-if"])


@router.post("", response_model=WhatIfResponse)
def run_what_if(conn: DbConn, req: WhatIfRequest) -> WhatIfResponse:
    """Simulate overbooking and a cancellation-risk-based deposit policy (G4).

    Returns recovered revenue, nights at risk of overselling, estimated walk cost, net benefit,
    the benefit curve by overbooking level and the recommended level. Formulas: the docstring of
    `app/services/what_if_service.py`. Read-only: nothing is written to the DB.
    """
    return what_if_service.run_what_if(conn, req)
