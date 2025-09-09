# app/guard.py
import re

# 🔥 Список опасных фраз (jailbreak / инъекции)
JAILBREAK_KEYWORDS = [
    "игнорируй предыдущие инструкции",
    "ignore all previous instructions",
    "act as",
    "you are now",
    "bypass",
    "override",
    "DAN",
    "do anything now",
    "режим разработчика",
    "developer mode",
    "не соблюдай правила",
    "наруши правила",
    "pretend you are",
    "simulate",
]

# 🚫 Список запрещённых тем (можно расширить)
BANNED_TOPICS = [
    "взлом",
    "hack",
    "наркотики",
    "drugs",
    "самоубийство",
    "suicide",
    "оружие",
    "weapon",
    "мошенничество",
    "fraud"
]

def detect_jailbreak(prompt: str) -> dict:
    prompt_lower = prompt.lower()
    
    # Проверка по ключевым фразам
    for keyword in JAILBREAK_KEYWORDS:
        if keyword in prompt_lower:
            return {
                "flagged": True,
                "reason": "jailbreak_attempt",
                "risk_score": 0.95,
                "suggested_rewrite": "Я не могу выполнить этот запрос. Давайте обсудим что-то безопасное и полезное."
            }
    
    # Проверка по запрещённым темам
    for topic in BANNED_TOPICS:
        if topic in prompt_lower:
            return {
                "flagged": True,
                "reason": "harmful_content",
                "risk_score": 0.85,
                "suggested_rewrite": "Эта тема выходит за рамки моих возможностей. Чем ещё я могу помочь?"
            }
    
    # Безопасный промпт
    return {
        "flagged": False,
        "reason": "safe",
        "risk_score": 0.0,
        "suggested_rewrite": prompt  # возвращаем оригинальный
    }
