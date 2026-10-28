from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Read values from the .env file in the backend folder
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (these names match your .env lines).
    # No defaults: every value must come from .env, or the app refuses to start.
    database_name: str
    database_user: str
    database_password: str
    database_host: str
    database_port: int

    # The website address allowed to call this API
    frontend_origin: str
    
    # JWT (login tokens)
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_issuer: str
    jwt_audience: str
    access_token_expire_minutes: int
    
    # Brute-force protection
    max_failed_login_attempts: int
    account_lockout_minutes: int



    @property
    def database_url(self) -> str:
        # Joins the parts into: postgresql+psycopg://user:password@host:port/name
        password = quote_plus(self.database_password)
        return (
            f"postgresql+psycopg://{self.database_user}:{password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


settings = Settings()
