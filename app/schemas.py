"""
Data schemas and API request/response contracts using Pydantic.
Ensures validation of input variables and prevents type coercion errors.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, constr

class RouteRequest(BaseModel):
    # Length limits prevent long-input prompt injection attacks
    query: constr(min_length=2, max_length=250) = Field(
        ..., 
        description="Colloquial navigation request (e.g., 'Spanish instructions to train station avoiding stairs')"
    )
    language: constr(min_length=2, max_length=5) = Field(
        "en", 
        description="Language code for output instructions (e.g., 'en', 'es', 'fr', 'ja')"
    )
    wheelchair_accessible: bool = Field(
        False, 
        description="Set to true to bypass stairs, escalators, and steep paths"
    )
    current_section: str = Field(
        ..., 
        description="Current seating section or gate inside the stadium (e.g., 'Section 104', 'Gate A')"
    )
    destination: str = Field(
        ..., 
        description="Target location (e.g., 'Train Station', 'Rideshare Hub', 'Main Parking', 'Gate B')"
    )

class RouteStep(BaseModel):
    step_number: int = Field(..., description="Order of the step in the route")
    instruction: str = Field(..., description="Human-friendly wayfinding instruction")
    congested: bool = Field(..., description="Whether this section of the path is currently congested")
    estimated_seconds: int = Field(..., description="Estimated travel time for this leg")

class RouteResponse(BaseModel):
    route_found: bool = Field(..., description="Whether a valid route could be constructed")
    language: str = Field(..., description="Language code of returned instructions")
    path_taken: List[str] = Field(..., description="Ordered list of node IDs visited")
    steps: List[RouteStep] = Field(..., description="Step-by-step description of the path")
    total_distance_meters: float = Field(..., description="Total length of path in meters")
    total_time_minutes: float = Field(..., description="Estimated travel time including congestion penalties")
    genai_narrative: str = Field(..., description="GenAI generated context-aware narrative and advice")
    is_cached: bool = Field(False, description="Whether the response was served from the cache")
    fallback_used: bool = Field(False, description="Whether a local fallback rule was triggered due to LLM error")

class SensorUpdate(BaseModel):
    node_id: str = Field(..., description="ID of the graph node (e.g., 'gate_a', 'sec_104')")
    crowd_density: str = Field(..., description="Crowd density status ('LOW', 'MEDIUM', 'HIGH')")
    elevator_operational: Optional[bool] = Field(None, description="Status of the elevator, if this is an elevator node")

class APIStatus(BaseModel):
    status: str = Field(..., description="API operational status")
    stadium: str = Field(..., description="Target stadium name")
    mock_llm: bool = Field(..., description="Whether system is operating in mock fallback mode")
