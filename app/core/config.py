from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Peroxia Technology Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "SUPER_SECRET_KEY_FOR_JWT_THAT_SHOULD_BE_CHANGED_IN_PROD"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./peroxia.db"

    class Config:
        case_sensitive = True

settings = Settings()
