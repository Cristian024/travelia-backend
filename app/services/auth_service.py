from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import UserDocument, UserRole
from app.ports.repositories import UserRepositoryPort
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(
        self, user_repo: UserRepositoryPort, admin_emails: list[str] | None = None
    ) -> None:
        self._repo = user_repo
        self._admin_emails = {e.lower() for e in (admin_emails or [])}

    async def register(self, request: RegisterRequest) -> TokenResponse:
        if await self._repo.email_exists(request.email):
            raise ConflictError("Email already registered")

        email = request.email.lower()
        user = UserDocument(
            email=email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            birth_date=request.birth_date,
            country_of_residence=request.country_of_residence,
            phone=request.phone,
            preferred_language=request.preferred_language,
            role=UserRole.admin if email in self._admin_emails else UserRole.user,
        )
        user_id = await self._repo.insert(user)
        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )

    async def login(self, request: LoginRequest) -> TokenResponse:
        user = await self._repo.find_by_email(request.email)
        if not user or not verify_password(request.password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials")

        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise UnauthorizedError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token payload")

        user = await self._repo.find_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found")

        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )
