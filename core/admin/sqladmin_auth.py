from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request


from core import settings


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]

        # Validate username/password credentials
        if username == settings.admin_panel.username and password == settings.admin_panel.password:
            # And update session
            request.session.update({"token": "authenticated"})
            return True

        return False

    async def logout(self, request: Request) -> bool:
        # Clear the session
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")

        if token == "authenticated":
            return True

        return False


# Create the authentication backend instance
sqladmin_authentication_backend = AdminAuth(secret_key=settings.admin_panel.secret_key)
