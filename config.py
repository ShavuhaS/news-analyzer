from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    # Kafka configuration
    KAFKA_BROKERS: str = Field(default="localhost:9092", env="KAFKA_BROKERS")
    KAFKA_NEWS_TOPIC: str = Field(default="news-parsed", env="KAFKA_NEWS_TOPIC")
    KAFKA_ANALYZED_TOPIC: str = Field(default="news-analyzed", env="KAFKA_ANALYZED_TOPIC")
    KAFKA_GROUP_ID: str = Field(default="analyzer-service-group", env="KAFKA_GROUP_ID")
    
    # Analysis settings
    SPACY_MODEL: str = "uk_core_news_trf"
    USE_GPU: bool = True
    
    # Geocoding settings
    GEONAMES_USERNAME: str = Field(default="demo", env="GEONAMES_USERNAME")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
