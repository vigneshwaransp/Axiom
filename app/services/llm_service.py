"""
GenAI Orchestration Service.
Interacts with the Google Gemini API to compile and translate natural language route narratives.
Features a high-fidelity local multilingual generator as a fallback for offline/low-bandwidth stadium conditions.
"""

import logging
from typing import Dict, List, Tuple
from app.config import settings
from app.schemas import RouteStep

logger = logging.getLogger("app.llm_service")

# Translation and localization assets for high-fidelity fallback
LOCALIZED_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "intro": "Welcome to FIFA World Cup 2026 Egress Operations. Your navigation route from {start} to {dest} is ready.",
        "accessible": "This route is fully wheelchair-accessible.",
        "standard": "This route contains stairs or escalators.",
        "congested_warning": "Warning: Congested areas detected along your route (marked in orange/red). Proceed with caution and follow stadium staff instructions.",
        "clear_path": "The path is relatively clear. Expect a smooth walk.",
        "time_summary": "Estimated walking time is approximately {minutes} minutes over a distance of {meters} meters.",
        "outro": "Have a safe trip home, and thank you for attending the World Cup 2026!"
    },
    "es": {
        "intro": "Bienvenido a Operaciones de Salida de la Copa Mundial de la FIFA 2026. Su ruta de navegación desde {start} hasta {dest} está lista.",
        "accessible": "Esta ruta es totalmente accesible para sillas de ruedas.",
        "standard": "Esta ruta contiene escaleras o escaleras mecánicas.",
        "congested_warning": "Advertencia: Se detectaron áreas congestionadas en su ruta (marcadas en naranja/rojo). Proceda con precaución y siga las instrucciones del personal del estadio.",
        "clear_path": "El camino está relativamente despejado. Se espera una caminata fluida.",
        "time_summary": "El tiempo estimado de caminata es de aproximadamente {minutes} minutos a lo largo de una distancia de {meters} metros.",
        "outro": "¡Tenga un viaje seguro a casa y gracias por asistir a la Copa Mundial de la FIFA 2026!"
    },
    "fr": {
        "intro": "Bienvenue aux opérations de sortie de la Coupe du Monde de la FIFA 2026. Votre itinéraire de navigation de {start} à {dest} est prêt.",
        "accessible": "Cet itinéraire est entièrement accessible en fauteuil roulant.",
        "standard": "Cet itinéraire contient des escaliers ou des escalators.",
        "congested_warning": "Attention: Des zones congestionnées ont été détectées sur votre parcours (indiquées en orange/rouge). Progressez avec prudence et suivez les consignes des stadiers.",
        "clear_path": "Le chemin est relativement dégagé. Attendez-vous à une marche fluide.",
        "time_summary": "Le temps de marche estimé est d'environ {minutes} minutes pour une distance de {meters} mètres.",
        "outro": "Bon retour chez vous et merci d'avoir assisté à la Coupe du Monde de la FIFA 2026 !"
    },
    "ja": {
        "intro": "FIFAワールドカップ2026退場オペレーションへようこそ。{start}から{dest}への移動ルートが準備できました。",
        "accessible": "このルートは車椅子で完全にご利用いただけます。",
        "standard": "このルートには階段またはエスカレーターが含まれています。",
        "congested_warning": "警告：ルート上に混雑エリア（オレンジ/赤で表示）が検出されました。注意して進み、スタジアムの係員の指示に従ってください。",
        "clear_path": "経路は比較的空いています。スムーズに進むことができます。",
        "time_summary": "推定徒歩時間は、距離 {meters} メートルに対して約 {minutes} 分です。",
        "outro": "安全なご帰宅をお祈りいたします。ワールドカップ2026へのご来場ありがとうございました！"
    }
}

class LLMService:
    @staticmethod
    def get_narrative(
        start: str,
        dest: str,
        wheelchair: bool,
        steps: List[RouteStep],
        meters: float,
        minutes: float,
        language: str = "en"
    ) -> Tuple[str, bool]:
        """
        Generates a human-friendly narrative summarizing the route and current crowd warnings.
        First attempts to use Google Gemini, then falls back to local translation models.
        
        Returns:
            Tuple of:
            - narrative_text (str)
            - fallback_used (bool)
        """
        lang = language.lower() if language.lower() in LOCALIZED_TEMPLATES else "en"
        
        # Build contextual data to provide to LLM
        congested_count = sum(1 for s in steps if s.congested)
        accessibility_type = "accessible" if wheelchair else "standard"
        
        # If mock mode is forced, run fallback directly to save latency and costs
        if settings.USE_MOCK_LLM:
            return LLMService._generate_fallback(start, dest, wheelchair, meters, minutes, lang, congested_count), True

        # Live GenAI Execution Block
        try:
            import google.generativeai as genai
            
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "mock_key":
                raise ValueError("Valid Gemini API key not configured in environment variables.")

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            # System prompt ensures strict response constraints and avoids Hallucinations
            prompt = (
                f"You are the official multilingual voice of FIFA World Cup 2026 Stadium Operations.\n"
                f"Summarize the following navigation route for a fan in a professional, clear, and friendly tone.\n"
                f"Your response must be entirely in the language corresponding to language code: {lang}.\n\n"
                f"Route Details:\n"
                f"- Start: {start}\n"
                f"- Destination: {dest}\n"
                f"- Wheelchair Accessible Route Required: {wheelchair}\n"
                f"- Total Distance: {meters} meters\n"
                f"- Estimated Time: {minutes} minutes\n"
                f"- Total path steps: {len(steps)}\n"
                f"- Number of congested steps: {congested_count}\n\n"
                f"Instructions:\n"
                f"1. Explain the accessibility status (wheelchair vs standard).\n"
                f"2. Clearly warn them about crowd congestion if congested steps > 0.\n"
                f"3. Advise them to proceed safely and thank them for attending the World Cup.\n"
                f"4. Keep the summary under 120 words."
            )
            
            response = model.generate_content(prompt)
            if response.text:
                return response.text.strip(), False
            else:
                raise ValueError("Empty response received from LLM service.")

        except Exception as e:
            logger.warning(f"GenAI Live Call failed (error: {e}). Invoking high-fidelity localized fallback.")
            # Graceful degradation fallback
            return LLMService._generate_fallback(start, dest, wheelchair, meters, minutes, lang, congested_count), True

    @staticmethod
    def _generate_fallback(
        start: str,
        dest: str,
        wheelchair: bool,
        meters: float,
        minutes: float,
        lang: str,
        congested_count: int
    ) -> str:
        """Constructs a natural sounding paragraph using dynamic templates."""
        t = LOCALIZED_TEMPLATES[lang]
        
        intro = t["intro"].format(start=start, dest=dest)
        acc = t["accessible"] if wheelchair else t["standard"]
        congestion_warn = t["congested_warning"] if congested_count > 0 else t["clear_path"]
        summary = t["time_summary"].format(minutes=minutes, meters=int(meters))
        outro = t["outro"]

        # Assemble cohesive narrative
        narrative = f"{intro} {acc} {summary} {congestion_warn} {outro}"
        return narrative
