from pydantic import EmailStr
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
	# SMTP
	SMTP_HOST: str = "smtp.gmail.com"
	SMTP_PORT: int = 465
	SMTP_USER: str = ""
	SMTP_PASS: str = ""
	SMTP_FROM: EmailStr | None = None
	SMTP_SUBJECT_PREFIX: str = "SAE"

	# DB (se mantienen para compatibilidad con entorno existente)
	DB_USER: str = ""
	DB_PASSWORD: str = ""
	DB_HOST: str = ""
	DB_PORT: int = 1433
	DB_NAME: str = ""
	DB_DRIVER: str = "ODBC Driver 17 for SQL Server"

	model_config = {
		"env_file": ".env",
		"case_sensitive": False,
		"extra": "ignore"  # Ignorar variables no declaradas futuras
	}

	@property
	def effective_from(self) -> str:
		return self.SMTP_FROM or self.SMTP_USER

@lru_cache()
def get_settings() -> Settings:
	return Settings()  # Carga desde .env

settings = get_settings()
