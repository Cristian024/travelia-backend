from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.user import UserDocument, UserRole
from app.ports.repositories import UserRepositoryPort
from app.schemas.user import (
    PaginatedUsersResponse,
    UpdateUserRequest,
    UserAdminResponse,
    UserResponse,
)


class UserService:
    def __init__(self, user_repo: UserRepositoryPort) -> None:
        self._repo = user_repo

    async def get_profile(self, user_id: str) -> UserResponse:
        user = await self._repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        return _to_response(user)

    async def update_profile(self, user_id: str, request: UpdateUserRequest) -> UserResponse:
        user = await self._repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")

        updates = request.model_dump(exclude_none=True)
        if not updates:
            return _to_response(user)

        updates["updated_at"] = datetime.utcnow()
        await self._repo.update_by_id(user_id, updates)

        updated = await self._repo.find_by_id(user_id)
        return _to_response(updated)

    # --- Administración ---

    async def list_users(self, page: int, page_size: int) -> PaginatedUsersResponse:
        offset = (page - 1) * page_size
        users = await self._repo.list_all(limit=page_size, offset=offset)
        total = await self._repo.count_all()
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return PaginatedUsersResponse(
            items=[_to_admin(u) for u in users],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def update_role(self, user_id: str, role: UserRole) -> UserAdminResponse:
        user = await self._repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        await self._repo.update_by_id(
            user_id, {"role": role.value, "updated_at": datetime.utcnow()}
        )
        updated = await self._repo.find_by_id(user_id)
        return _to_admin(updated)


def _to_response(user: UserDocument) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        birth_date=user.birth_date,
        country_of_residence=user.country_of_residence,
        phone=user.phone,
        preferred_language=user.preferred_language,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _to_admin(user: UserDocument) -> UserAdminResponse:
    return UserAdminResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        subscription_type=user.subscription_type,
        premium_since=user.premium_since,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
