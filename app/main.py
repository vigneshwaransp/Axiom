"""
Main FastAPI application entry point.
Registers routing endpoints, implements safety guards, and serves the static Web client.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.schemas import RouteRequest, RouteResponse, SensorUpdate, APIStatus
from app.utils.security import SecurityUtils, rate_limit_dependency
from app.services.cache_service import cache_service
from app.services.crowd_sensor import stadium_graph
from app.services.route_service import RouteService
from app.services.llm_service import LLMService

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

app = FastAPI(
    title="FIFA World Cup 2026 Stadium Operations Gateway",
    description="GenAI-Powered Multilingual Egress Wayfinding & Crowd Navigation API",
    version="1.0.0"
)

# CORS middleware for Web client integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/api/status", response_model=APIStatus)
def get_status():
    """Retrieve API status metrics and runtime configuration details."""
    return APIStatus(
        status="OPERATIONAL",
        stadium=settings.STADIUM_NAME,
        mock_llm=settings.USE_MOCK_LLM
    )

@app.post("/api/route", response_model=RouteResponse, dependencies=[Depends(rate_limit_dependency)])
def get_route(request_body: RouteRequest):
    """
    Computes accessibility-safe path and queries GenAI for multilingual layout explanation.
    Protects LLM resources by applying security filters and caching strategies.
    """
    # 1. Sanitize input to mitigate XSS
    sanitized_query = SecurityUtils.sanitize_input(request_body.query)
    
    # 2. Check for Prompt Injection attempts
    if SecurityUtils.detect_prompt_injection(sanitized_query) or SecurityUtils.detect_prompt_injection(request_body.query):
        logger.warning("Adversarial payload detected in wayfinding request!")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suspicious query keywords detected. Please enter normal navigation queries."
        )

    # 3. Check Cache
    cache_key = (
        f"route_{request_body.current_section}_{request_body.destination}"
        f"_{request_body.wheelchair_accessible}_{request_body.language}"
    )
    cached_response = cache_service.get(cache_key)
    if cached_response:
        logger.info(f"Serving cached routing response for key: {cache_key}")
        # Return a copy with is_cached set to True
        response_data = RouteResponse(**cached_response)
        response_data.is_cached = True
        return response_data

    # 4. Route Graph Calculation
    success, path, steps, distance, minutes = RouteService.calculate_route(
        start_id=request_body.current_section.lower().replace(" ", "_"),
        destination_id=request_body.destination.lower().replace(" ", "_"),
        wheelchair_accessible=request_body.wheelchair_accessible
    )

    if not success:
        logger.info(f"Failed to find route from {request_body.current_section} to {request_body.destination}")
        return RouteResponse(
            route_found=False,
            language=request_body.language,
            path_taken=[],
            steps=[],
            total_distance_meters=0.0,
            total_time_minutes=0.0,
            genai_narrative="Route not found. Please verify start and destination names or contact stadium assistance.",
            is_cached=False,
            fallback_used=True
        )

    # 5. Get GenAI Narrative (or fallback)
    narrative, fallback_used = LLMService.get_narrative(
        start=request_body.current_section,
        dest=request_body.destination,
        wheelchair=request_body.wheelchair_accessible,
        steps=steps,
        meters=distance,
        minutes=minutes,
        language=request_body.language
    )

    # Create response object
    response_obj = RouteResponse(
        route_found=True,
        language=request_body.language,
        path_taken=path,
        steps=steps,
        total_distance_meters=distance,
        total_time_minutes=minutes,
        genai_narrative=narrative,
        is_cached=False,
        fallback_used=fallback_used
    )

    # 6. Save in Cache
    cache_service.set(
        cache_key, 
        response_obj.model_dump(), 
        ttl_seconds=settings.ROUTE_CACHE_TTL
    )

    return response_obj

@app.post("/api/sensor/update")
def update_sensor(sensor_body: SensorUpdate):
    """
    Updates stadium graph node congestion parameters.
    Used by simulation feeds to adjust routing logic dynamically.
    """
    success = stadium_graph.update_sensor(
        node_id=sensor_body.node_id,
        crowd_density=sensor_body.crowd_density,
        elevator_operational=sensor_body.elevator_operational
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {sensor_body.node_id} does not exist in the stadium layout graph."
        )
    cache_service.clear()
    return {"status": "SUCCESS", "message": f"Sensor parameters updated for node {sensor_body.node_id}"}

# Serve the static UI files from the web root
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
