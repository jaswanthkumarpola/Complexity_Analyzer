"""
Pydantic schemas for all API request and response models.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BoundType(str, Enum):
    BIG_O = "O"          # Asymptotic upper bound
    BIG_OMEGA = "Ω"      # Asymptotic lower bound
    BIG_THETA = "Θ"      # Asymptotically tight bound
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNKNOWN = "Unknown"


class AnalysisMethod(str, Enum):
    STATIC_ONLY = "static_only"
    AI_ASSISTED = "ai_assisted"
    FALLBACK = "fallback"
    HYBRID = "hybrid"


class DetectionMethod(str, Enum):
    USER_SELECTED = "user_selected"
    EXTENSION = "extension"
    PYGMENTS = "pygments"
    HEURISTIC = "heuristic"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AnalysisSettings(BaseModel):
    """Optional knobs the caller can adjust."""
    include_optimizations: bool = True
    include_visualization: bool = True
    max_explanation_length: int = Field(default=2000, ge=100, le=8000)


class AnalyzeRequest(BaseModel):
    """POST /api/analyze request body."""
    code: str = Field(..., min_length=1, description="Source code to analyze")
    language: Optional[str] = Field(
        None, description="Override language detection (language identifier)"
    )
    filename: Optional[str] = Field(None, description="Optional original filename")
    settings: AnalysisSettings = Field(default_factory=AnalysisSettings)

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Source code must not be empty or whitespace only.")
        return v


class DetectLanguageRequest(BaseModel):
    """POST /api/detect-language request body."""
    code: str = Field(..., min_length=1)
    filename: Optional[str] = None


# ---------------------------------------------------------------------------
# Sub-models used in responses
# ---------------------------------------------------------------------------

class ComplexityEstimate(BaseModel):
    """A single complexity estimate (time or space)."""
    expression: str = Field(..., description="e.g. O(n log n)")
    bound_type: BoundType = BoundType.BIG_O
    justification: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    evidence: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class CaseComplexity(BaseModel):
    """Best / average / worst case analysis."""
    best_case: Optional[ComplexityEstimate] = None
    average_case: Optional[ComplexityEstimate] = None
    worst_case: Optional[ComplexityEstimate] = None
    notes: str = ""


class StaticEvidence(BaseModel):
    """Findings from static structural analysis."""
    loops: List[Dict[str, Any]] = Field(default_factory=list)
    nested_loops: List[Dict[str, Any]] = Field(default_factory=list)
    recursive_calls: List[Dict[str, Any]] = Field(default_factory=list)
    dominant_operations: List[str] = Field(default_factory=list)
    input_variables: List[str] = Field(default_factory=list)
    library_calls: List[str] = Field(default_factory=list)
    memory_allocations: List[Dict[str, Any]] = Field(default_factory=list)
    early_exits: bool = False
    has_sorting: bool = False
    has_binary_search: bool = False
    has_divide_conquer: bool = False
    parser_used: Optional[str] = None
    parse_errors: List[str] = Field(default_factory=list)


class OptimizationSuggestion(BaseModel):
    """A single optimization recommendation."""
    title: str
    issue_description: str
    evidence: str = ""
    proposed_change: str
    time_complexity_impact: str = ""
    space_complexity_impact: str = ""
    trade_offs: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    code_snippet: Optional[str] = None


class VisualizationData(BaseModel):
    """Data required to draw the complexity chart."""
    predicted_class: Optional[str] = None
    predicted_class_label: Optional[str] = None
    x_values: List[float] = Field(default_factory=list)
    curves: Dict[str, List[float]] = Field(default_factory=dict)
    highlight_curve: Optional[str] = None
    x_axis_label: str = "Input size (n)"
    y_axis_label: str = "Operations (relative)"
    disclaimer: str = (
        "This chart illustrates asymptotic growth rates, "
        "not measured execution time."
    )


class LanguageInfo(BaseModel):
    """Language detection result."""
    identifier: str
    display_name: str
    detection_method: DetectionMethod = DetectionMethod.UNKNOWN
    detection_confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    parser_available: bool = False
    static_analysis_available: bool = False
    known_limitations: List[str] = Field(default_factory=list)


class ProviderStatus(BaseModel):
    """Information about the AI provider used."""
    provider: str
    model: Optional[str] = None
    ai_used: bool = False
    fallback_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Main analysis response
# ---------------------------------------------------------------------------

class AnalysisResponse(BaseModel):
    """POST /api/analyze and POST /api/analyze-file response."""
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    language: LanguageInfo
    analysis_method: AnalysisMethod
    provider_status: ProviderStatus

    time_complexity: ComplexityEstimate
    space_complexity: ComplexityEstimate
    case_analysis: CaseComplexity

    static_evidence: StaticEvidence
    explanation: str = ""
    assumptions: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN

    optimizations: List[OptimizationSuggestion] = Field(default_factory=list)
    visualization: Optional[VisualizationData] = None

    warnings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Other endpoint responses
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    app_name: str
    ai_provider_configured: bool
    analysis_modes: List[str]


class LanguageCapability(BaseModel):
    identifier: str
    display_name: str
    extensions: List[str]
    parser_available: bool
    static_analysis: bool
    known_limitations: List[str] = Field(default_factory=list)


class LanguagesResponse(BaseModel):
    languages: List[LanguageCapability]
    total: int


class DetectLanguageResponse(BaseModel):
    language: str
    display_name: str
    confidence: ConfidenceLevel
    detection_method: DetectionMethod


class ConfigStatusResponse(BaseModel):
    ai_provider_configured: bool
    ai_provider: str
    ai_model: str
    analysis_modes_available: List[str]
    max_code_size_kb: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
