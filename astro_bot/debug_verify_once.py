import json
from flow_manager import AstroFlowOrchestrator

# Минимальный фиктивный кейс для прогона пайплайна без Telegram.
# Замени знаки/аспекты на свои реальные (из распознанного JSON), если нужно.
SAMPLE = {
    "client_1": {
        "name": "Partner 1",
        "sun": "Близнецы",
        "moon": "Рыбы",
        "mercury": "Телец",
        "venus": "Телец",
        "mars": "Скорпион",
        "jupiter": "Рак",
        "saturn": "Скорпион",
        "uranus": "Стрелец",
        "neptune": "Козерог",
        "pluto": "Скорпион",
        "lilith": None,
        "north_node": "Близнецы",
        "ascendant": "Лев",
    },
    "client_2": {
        "name": "Partner 2",
        "sun": "Скорпион",
        "moon": "Рыбы",
        "mercury": "Скорпион",
        "venus": "Весы",
        "mars": "Стрелец",
        "jupiter": "Дева",
        "saturn": "Весы",
        "uranus": "Скорпион",
        "neptune": "Стрелец",
        "pluto": "Весы",
        "lilith": None,
        "north_node": "Лев",
        "ascendant": "Близнецы",
    },
    "aspects": [
        "Moon (Partner 1) Conjunction Moon (Partner 2)",
        "Mercury (Partner 1) Opposition Mercury (Partner 2)",
        "Mars (Partner 1) Quincunx Mars (Partner 2)",
    ],
    "missing": {"client_1": [], "client_2": []},
    "status": "Unknown",
}


def main():
    orch = AstroFlowOrchestrator()
    text, issues = orch.process_compatibility_report(SAMPLE)

    print("\n=== FINAL TEXT (first 800 chars) ===\n")
    print(text[:800])

    print("\n=== ISSUES ===\n")
    print(json.dumps(issues, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
