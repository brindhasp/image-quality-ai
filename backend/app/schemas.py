from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    severity: str
    confidence: float
    explanation: str


class StatisticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    width: int
    height: int
    sharpness: float
    brightness: float
    contrast: float
    noise: float
    dark_pixel_ratio: float
    bright_pixel_ratio: float
    saturation_ratio: float
    edge_density: float


class ModelInfo(BaseModel):
    name: str
    version: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    quality_score: float
    quality_label: str
    issues: List[IssueResponse]
    statistics: StatisticsResponse
    model: ModelInfo
    created_at: datetime


class AnalysisListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_size: int
    quality_score: float
    quality_label: str
    issues: List[IssueResponse]
    created_at: datetime


class AnalysisListResponse(BaseModel):
    items: List[AnalysisListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatisticsSummary(BaseModel):
    total_analyses: int
    average_score: float
    acceptable_count: int
    degraded_count: int
    defective_count: int
    most_common_issue: Optional[str]
    label_distribution: dict
    issue_distribution: dict
    recent_analyses: List[AnalysisListItem]


class BatchAnalysisResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[AnalysisResponse]
    errors: List[dict]


class ABTestResponse(BaseModel):
    model_a: ModelInfo
    model_b: ModelInfo
    test_image_id: int
    prediction_a: dict
    prediction_b: dict
    agreement: bool


class ModelVersionInfo(BaseModel):
    version: str
    loaded: bool
    accuracy: Optional[float] = None
    total_predictions: int = 0
