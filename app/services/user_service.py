from datetime import datetime
from app.core.exceptions import NotFoundError
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.schemas.user import UpdateUserRequest, UserResponse


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
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


def _to_response(user: UserDocument) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        birth_date=user.birth_date,
        country_of_residence=user.country_of_residence,
        phone=user.phone,
        preferred_language=user.preferred_language,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
