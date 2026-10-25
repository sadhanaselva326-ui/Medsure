from typing import Generic, List, Optional, TypeVar, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int = Field(1, description="Current page number")
    limit: int = Field(20, description="Items per page")
    total: int = Field(..., description="Total items matching query")
    total_pages: int = Field(..., description="Total number of pages")


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context or validation errors")


class ErrorResponse(BaseModel):
    error: ErrorDetail
