"""
LLM and Fallback Service unit tests.
Verifies translation template loading, multilingual text generation, and fallback logic.
"""

from app.services.llm_service import LLMService
from app.schemas import RouteStep

def test_local_fallback_generation_en():
    """Verify English narrative is formatted and contains metric details."""
    steps = [
        RouteStep(step_number=1, instruction="Walk to Gate A", congested=False, estimated_seconds=120)
    ]
    narrative, fallback = LLMService.get_narrative(
        start="Section 101",
        dest="Train Station",
        wheelchair=False,
        steps=steps,
        meters=150.0,
        minutes=2.5,
        language="en"
    )
    
    assert fallback is True  # Since mock is default active in tests
    assert "Section 101" in narrative
    assert "Train Station" in narrative
    assert "2.5 minutes" in narrative
    assert "150 meters" in narrative
    assert "stairs or escalators" in narrative

def test_local_fallback_generation_es():
    """Verify Spanish narrative utilizes Spanish templates."""
    steps = [
        RouteStep(step_number=1, instruction="Walk to Gate A", congested=True, estimated_seconds=120)
    ]
    narrative, fallback = LLMService.get_narrative(
        start="Section 101",
        dest="Train Station",
        wheelchair=True,
        steps=steps,
        meters=150.0,
        minutes=3.2,
        language="es"
    )
    
    assert fallback is True
    assert "totalmente accesible" in narrative
    assert "Advertencia: Se detectaron" in narrative

def test_local_fallback_unsupported_language_degrades_to_en():
    """Verify passing unsupported language fallback defaults to English."""
    steps = [
        RouteStep(step_number=1, instruction="Walk to Gate A", congested=False, estimated_seconds=60)
    ]
    narrative, fallback = LLMService.get_narrative(
        start="Section 101",
        dest="Train Station",
        wheelchair=False,
        steps=steps,
        meters=50.0,
        minutes=1.0,
        language="de"  # German is not in supported languages
    )
    
    assert fallback is True
    assert "Welcome to FIFA World Cup" in narrative  # English text
