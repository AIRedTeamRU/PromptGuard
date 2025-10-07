# app/guard.py
import re
import unicodedata
import joblib
import os
from pathlib import Path

# ==============================
# 1. ПУТИ К МОДЕЛЯМ
# ==============================

# Определяем путь к папке с моделями (рядом с guard.py)
BASE_DIR = Path(__file__).parent
VECTORIZER_PATH = BASE_DIR / "tfidf_vectorizer.pkl"
CLASSIFIER_PATH = BASE_DIR / "jailbreak_classifier.pkl"

# Проверяем наличие файлов
if not VECTORIZER_PATH.exists() or not CLASSIFIER_PATH.exists():
    raise FileNotFoundError(
        f"Не найдены файлы модели! Убедитесь, что {VECTORIZER_PATH} и {CLASSIFIER_PATH} находятся в папке 'app'."
    )

# Загружаем модели один раз при импорте
vectorizer = joblib.load(VECTORIZER_PATH)
classifier = joblib.load(CLASSIFIER_PATH)

# ==============================
# 2. ПРЕДОБРАБОТКА ТЕКСТА
# ==============================

def normalize_unicode(text: str) -> str:
    """Удаляет эмодзи и невидимые символы"""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'So' and not unicodedata.combining(c)
    )

def leet_to_text(text: str) -> str:
    """Преобразует leet-язык в обычный текст"""
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
    """Полная нормализация текста"""
    text = normalize_unicode(text)
    text = leet_to_text(text)
    text = re.sub(r'[^а-яёa-z\s]', ' ', text, flags=re.IGNORECASE)
    return ' '.join(text.split()).lower()

# ==============================
# 3. REGEX-ФИЛЬТР (резервная защита)
# ==============================

JAILBREAK_PATTERNS = [
    r'\b(ignore\s+(all\s+)?(previous\s+)?instructions?)\b',
    r'\b(developer\s+mode|режим\s+разработчика)\b',
    r'\b(DAN|Do\s+Anything\s+Now)\b',
    r'\b(наруши\s+правила|обойди\s+фильтр|игнорируй\s+инструкции)\b',
]

def regex_check(prompt: str) -> bool:
    cleaned = prompt.lower()
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return True
    return False

# ==============================
# 4. ОСНОВНАЯ ФУНКЦИЯ
# ==============================

def detect_jailbreak(prompt: str) -> dict:
    # 🔥 Быстрая проверка по regex (для явных атак)
    if regex_check(prompt):
        return {
            "flagged": True,
            "reason": "jailbreak_regex",
            "risk_score": 0.95,
            "suggested_rewrite": "Я не могу выполнить этот запрос. Давайте обсудим что-то безопасное."
        }

    # 📊 TF-IDF + классификатор
    try:
        cleaned = clean_text(prompt)
        X = vectorizer.transform([cleaned])
        prob = classifier.predict_proba(X)[0][1]  # вероятность jailbreak
        is_jailbreak = prob > 0.7

        if is_jailbreak:
            return {
                "flagged": True,
                "reason": "jailbreak_tfidf",
                "risk_score": round(float(prob), 2),
                "suggested_rewrite": "Запрос заблокирован системой безопасности."
            }
    except Exception as e:
        # На случай ошибки в модели — безопасный fallback
        print(f"Ошибка в ML-модели: {e}")
        pass

    # ✅ Безопасно
    return {
        "flagged": False,
        "reason": "safe",
        "risk_score": 0.0,
        "suggested_rewrite": prompt
    }
