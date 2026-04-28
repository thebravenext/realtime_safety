from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'SafetyX Pro'
    app_env: str = Field(default='development', alias='APP_ENV')
    debug: bool = Field(default=True, alias='DEBUG')
    secret_key: str = Field(default='change-this-secret-key-before-production', alias='SECRET_KEY')
    database_url: str = Field(default='sqlite:///./ppe_db.sqlite3', alias='DATABASE_URL')
    ppe_model_path: str = Field(default='data/models/PPE_Model.pt', alias='PPE_MODEL_PATH')
    truck_model_path: str = Field(default='data/models/PPE_Model.pt', alias='TRUCK_MODEL_PATH')
    fire_model_path: str = Field(default='data/models/a.pt', alias='FIRE_MODEL_PATH')
    process_every_n_frames: int = Field(default=3, alias='PROCESS_EVERY_N_FRAMES')
    target_process_fps: float = Field(default=4.0, alias='TARGET_PROCESS_FPS')
    frame_width: int = Field(default=960, alias='FRAME_WIDTH')
    frame_height: int = Field(default=540, alias='FRAME_HEIGHT')
    jpeg_quality: int = Field(default=80, alias='JPEG_QUALITY')


@lru_cache
def get_settings() -> Settings:
    return Settings()
