from flow_manager import AstroFlowOrchestrator
import json

# Это симуляция данных, которые бот извлек бы из картинки/PDF
# В реальном боте здесь будет OCR или Vision LLM
MOCK_CLIENT_DATA = {
    "client_1": {
        "name": "Анна",
        "gender": "Female",
        "sun": "Козерог",
        "moon": "Рыбы",
        "mercury": "Козерог",
        "venus": "Стрелец",
        "mars": "Весы",
        "jupiter": "Стрелец",
        "saturn": "Рыбы"
    },
    "client_2": {
        "name": "Алексей",
        "gender": "Male",
        "sun": "Рыбы",
        "moon": "Лев",
        "mercury": "Овен",
        "venus": "Водолей",
        "mars": "Скорпион",
        "jupiter": "Близнецы", 
        "saturn": "Рыбы"
    },
    "aspects": [
        "Sun Sextile Sun",
        "Moon Quincunx Moon",
        "Venus Sextile Venus",
        "Mercury Square Mercury"
    ],
    "status": "Married pair" 
}

def main():
    print("Initializing Astro Bot Logic...")
    
    orchestrator = AstroFlowOrchestrator()
    
    report = orchestrator.process_compatibility_report(MOCK_CLIENT_DATA)
    
    orchestrator.save_to_file(report, "Result_Compatibility.txt")
    print("Process Finished.")

if __name__ == "__main__":
    main()
