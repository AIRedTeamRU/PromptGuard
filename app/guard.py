# app/guard.py
import re
import string
import unicodedata

# ==============================
# 1. УЛУЧШЕННАЯ ПРЕДОБРАБОТКА
# ==============================

def normalize_unicode(text: str) -> str:
    """Преобразует эмодзи и спецсимволы в читаемый текст (частично)"""
    # Удаляем эмодзи и невидимые символы
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'So' and not unicodedata.combining(c)
    )

def leet_to_text(text: str) -> str:
    """Преобразует простой leet-язык в обычный текст"""
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
    """Полная нормализация: эмодзи → удаление, leet → буквы, пунктуация → пробелы"""
    text = normalize_unicode(text)
    text = leet_to_text(text)
    # Заменяем всё, кроме букв и пробелов, на пробелы
    text = re.sub(r'[^а-яёa-z\s]', ' ', text, flags=re.IGNORECASE)
    # Убираем лишние пробелы
    return ' '.join(text.split()).lower()

# ==============================
# 2. РАСШИРЕННЫЕ СПИСКИ УГРОЗ
# ==============================

JAILBREAK_PATTERNS = [
    r'\b(act\s+as|pretend\s+to\s+be|simulate\s+as)\b',
    r'\b(developer\s+mode|режим\s+разработчика)\b',
    r'\b(ignore\s+(all\s+)?(previous\s+)?instructions?)\b',
    r'\b(bypass|override|circumvent)\s+(rules|restrictions|guidelines|filters)\b',
    r'\b(DAN|Do\s+Anything\s+Now|DAN\s+mode)\b',
    r'\b(не\s+соблюдай|наруши)\s+(правила|инструкции)\b',
]

# Токсичный контент: агрессия, ненависть, дискриминация
TOXIC_KEYWORDS = [
    "токсичный", "toxic", "ненависть", "hate", "расизм", "racism",
    "ксенофобия", "xenophobia", "гомофобия", "homophobia",
    "оскорб", "обид", "ненавид", "убей", "смерть", "die", "kill",
    "дурак", "идиот", "урод", "гад", "мерзавец", "сволочь"
]

# Запрещённые темы
BANNED_TOPICS = {
    "violence": ["оружие", "weapon", "взрыв", "bomb", "убийство", "murder", "насилие", "violence"],
    "drugs": ["наркотики", "drugs", "марихуана", "cannabis", "кокаин", "cocaine"],
    "self_harm": ["самоубийство", "suicide", "суицид", "self-harm", "жизнь не стоит"],
    "illegal": ["взлом", "hack", "мошенничество", "fraud", "киберпреступность", "phishing"],
}

# ==============================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================

def contains_word(text: str, word: str) -> bool:
    """Точное совпадение слова с границами"""
    return bool(re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE))

def count_toxic_words(text: str, keywords: list) -> int:
    """Считает количество токсичных слов (для оценки уровня)"""
    return sum(1 for word in keywords if contains_word(text, word))

# ==============================
# 4. ОСНОВНАЯ ФУНКЦИЯ
# ==============================

def detect_jailbreak(prompt: str) -> dict:
    # 🔍 Этап 1: Предобработка
    cleaned = clean_text(prompt)
    
    # 🔥 Этап 2: Проверка jailbreak-паттернов
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return {
                "flagged": True,
                "reason": "jailbreak_attempt",
                "risk_score": 0.95,
                "suggested_rewrite": "Я не могу выполнить этот запрос. Давайте обсудим что-то безопасное и полезное."
            }
    
    # ☠️ Этап 3: Проверка токсичного контента
    toxic_count = count_toxic_words(cleaned, TOXIC_KEYWORDS)
    if toxic_count >= 1:
        risk = min(0.7 + toxic_count * 0.1, 0.9)  # чем больше слов — тем выше риск
        return {
            "flagged": True,
            "reason": "toxic_content",
            "risk_score": round(risk, 2),
            "suggested_rewrite": "Пожалуйста, общайтесь уважительно. Чем могу помочь?"
        }
    
    # 🚫 Этап 4: Проверка запрещённых тем
    for category, words in BANNED_TOPICS.items():
        for word in words:
            if contains_word(cleaned, word):
                risk = 0.85 if category in ["violence", "drugs", "self_harm"] else 0.75
                return {
                    "flagged": True,
                    "reason": f"harmful_content_{category}",
                    "risk_score": risk,
                    "suggested_rewrite": "Эта тема выходит за рамки моих возможностей. Чем ещё я могу помочь?"
                }
    
    # ✅ Безопасно
    return {
        "flagged": False,
        "reason": "safe",
        "risk_score": 0.0,
        "suggested_rewrite": prompt
    }
