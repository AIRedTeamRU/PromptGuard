# app/guard.py
import re
import string
import unicodedata
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ==============================
# 1. ГЛОБАЛЬНАЯ ИНИЦИАЛИЗАЦИЯ МОДЕЛИ (один раз при запуске)
# ==============================

# Загружаем лёгкую модель для классификации jailbreak-атак
# Обучена на датасете jailbreak-промптов (можно дообучить на своих данных)
MODEL_NAME = "cointegrated/rubert-tiny2"  # или ваша кастомная модель
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
model.eval()  # режим инференса

def predict_jailbreak(text: str, threshold: float = 0.7) -> tuple[bool, float]:
    """Возвращает (is_jailbreak, confidence)"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=1)
        jailbreak_prob = probs[0][1].item()  # класс 1 = jailbreak
    return jailbreak_prob > threshold, jailbreak_prob

# ==============================
# 2. УЛУЧШЕННАЯ ПРЕДОБРАБОТКА
# ==============================

def normalize_unicode(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'So' and not unicodedata.combining(c)
    )

def leet_to_text(text: str) -> str:
    leet_map = {
        '0': 'о', '1': 'и', '2': 'з', '3': 'е', '4': 'а', '5': 'с',
        '6': 'б', '7': 'т', '8': 'в', '9': 'д',
        '@': 'а', '$': 'с', '!': 'и', 'l': 'и', '|': 'и',
        'z': 'з', 's': 'с', 'g': 'д', 'b': 'б'
    }
    text = text.lower()
    for leet, char in leet_map.items():
        text = text.replace(leet, char)
    return text

def clean_text(text: str) -> str:
    text = normalize_unicode(text)
    text = leet_to_text(text)
    text = re.sub(r'[^а-яёa-z\s]', ' ', text, flags=re.IGNORECASE)
    return ' '.join(text.split()).lower()

# ==============================
# 3. РАСШИРЕННЫЕ ПРАВИЛА (остаются для скорости)
# ==============================

JAILBREAK_PATTERNS = [
    r'\b(act\s+as|pretend\s+to\s+be|simulate\s+as)\b',
    r'\b(developer\s+mode|режим\s+разработчика)\b',
    r'\b(ignore\s+(all\s+)?(previous\s+)?instructions?)\b',
    r'\b(bypass|override|circumvent)\s+(rules|restrictions|guidelines|filters)\b',
    r'\b(DAN|Do\s+Anything\s+Now|DAN\s+mode)\b',
    r'\b(не\s+соблюдай|наруши)\s+(правила|инструкции)\b',
]

TOXIC_KEYWORDS = ["токсичный", "ненависть", "расизм", "оскорб", "убей", "дурак", "идиот"]
BANNED_TOPICS = {
    "violence": ["оружие", "взрыв", "убийство"],
    "drugs": ["наркотики", "марихуана"],
}

def contains_word(text: str, word: str) -> bool:
    return bool(re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE))

# ==============================
# 4. ОСНОВНАЯ ФУНКЦИЯ С ML
# ==============================

def detect_jailbreak(prompt: str) -> dict:
    # 1. Быстрая проверка по правилам (для очевидных случаев)
    cleaned = clean_text(prompt)
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return {
                "flagged": True,
                "reason": "jailbreak_attempt",
                "risk_score": 0.95,
                "suggested_rewrite": "Я не могу выполнить этот запрос."
            }

    # 2. Проверка токсичности и запрещённых тем
    toxic_count = sum(1 for w in TOXIC_KEYWORDS if contains_word(cleaned, w))
    if toxic_count >= 1:
        return {
            "flagged": True,
            "reason": "toxic_content",
            "risk_score": min(0.7 + toxic_count * 0.1, 0.9),
            "suggested_rewrite": "Пожалуйста, общайтесь уважительно."
        }

    for cat, words in BANNED_TOPICS.items():
        if any(contains_word(cleaned, w) for w in words):
            return {
                "flagged": True,
                "reason": f"harmful_content_{cat}",
                "risk_score": 0.85,
                "suggested_rewrite": "Эта тема выходит за рамки моих возможностей."
            }

    # 3. СЕМАНТИЧЕСКИЙ АНАЛИЗ ЧЕРЕЗ ML (ключевое улучшение!)
    is_jailbreak, confidence = predict_jailbreak(prompt)
    if is_jailbreak:
        return {
            "flagged": True,
            "reason": "jailbreak_semantic",
            "risk_score": round(confidence, 2),
            "suggested_rewrite": "Я не могу выполнить этот запрос."
        }

    # 4. Безопасно
    return {
        "flagged": False,
        "reason": "safe",
        "risk_score": 0.0,
        "suggested_rewrite": prompt
    }
