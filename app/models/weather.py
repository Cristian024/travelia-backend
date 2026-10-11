from typing import Optional

from pydantic import BaseModel, Field


class DailyForecast(BaseModel):
    date: str
    temp_min: float
    temp_max: float
    description: str
    icon: Optional[str] = None


class WeatherForecast(BaseModel):
    city: str
    country: str
    days: list[DailyForecast] = Field(default_factory=list)
    summary: str = ""
