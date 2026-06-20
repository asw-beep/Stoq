"""Admin-only endpoints.

Every route here is gated by ``require_role("admin")`` so only accounts whose
role is ``admin`` may call them. A standard ``user`` receives 403; an
unauthenticated caller receives 401 (enforced by ``get_current_user``).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.pagination import Pagination, pagination_params
from api.schemas import AdminUserOut, Page
from auth.dependencies import require_role
from auth.repository import UserRepository
from db.session import get_db
from models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=Page[AdminUserOut])
def list_users(
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> Page[AdminUserOut]:
    """List all registered users (admin only, paginated). No password hashes."""
    repo = UserRepository(db)
    items = [
        AdminUserOut.model_validate(u)
        for u in repo.list_users(limit=page.limit, offset=page.offset)
    ]
    return Page(
        items=items,
        total=repo.count_users(),
        limit=page.limit,
        offset=page.offset,
    )
