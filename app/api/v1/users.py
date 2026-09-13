from typing import Annotated
from fastapi import APIRouter, Depends
from app.dependencies import CurrentUser, get_user_service
from app.schemas.user import UpdateUserRequest, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    user_id: CurrentUser,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    return await service.get_profile(user_id)


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    body: UpdateUserRequest,
    user_id: CurrentUser,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    return await service.update_profile(user_id, body)
