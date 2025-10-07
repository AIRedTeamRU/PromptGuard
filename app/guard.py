# app/guard.py
import re
import unicodedata
import joblib
from pathlib import Path

# ==============================
# 1. ПУТИ К МОДЕЛЯМ
# ==============================

BASE_DIR = Path(__file__).parent
VECTORIZER_PATH = BASE_DIR / "tfidf_vectorizer.pkl"
CLASSIFIER_PATH = BASE_DIR / "jailbreak_classifier.pkl"

# Проверка наличия файлов
if not VECTORIZER_PATH.exists() or not CLASSIFIER_PATH.exists():
    raise FileNotFoundError(
        f"Не найдены файлы модели! Убедитесь, что {VECTORIZER_PATH} и {CLASSIFIER_PATH} находятся в папке 'app'."
    )

vectorizer = joblib.load(VECTORIZER_PATH)
classifier = joblib.load(CLASSIFIER_PATH)

# ==============================
# 2. СПИСКИ УГРОЗ
# ==============================

# Токсичный контент
TOXIC_KEYWORDS = [
    "оскорб", "обид", "дурак", "идиот", "урод", "гад", "мерзавец", "сволочь",
    "ненависть", "расизм", "ксенофобия", "гомофобия", "убей", "смерть", "насиль"
]

# Персональные данные (ПДн)
PDI_KEYWORDS = [
    "инн", "снилс", "паспорт", "номер карты", "cvv", "cvc", "дата рождения",
    "адрес проживания", "телефон", "email", "почта", "логин", "пароль"
]

# Запрещённые темы
BANNED_TOPICS = {
    "violence": ["оружие", "взрыв", "убийство", "насилие"],
    "drugs": ["наркотики", "марихуана", "кокаин"],
    "illegal": ["взлом", "мошенничество", "киберпреступность", "фishing", "фишинг"]
}

# ==============================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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

def contains_word(text: str, word: str) -> bool:
    return bool(re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE))

# ==============================
# 4. ОСНОВНАЯ ФУНКЦИЯ
# ==============================

def detect_jailbreak(prompt: str) -> dict:
    cleaned = clean_text(prompt)

    # 🔥 1. Быстрая проверка по regex (jailbreak)
    jailbreak_patterns = [
        r'\b(ignore\s+(all\s+)?(previous\s+)?instructions?)\b',
        r'\b(developer\s+mode|режим\s+разработчика)\b',
        r'\b(DAN|Do\s+Anything\s+Now)\b',
        r'\b(наруши\s+правила|обойди\s+фильтр)\b',
    ]
    for pattern in jailbreak_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return {
                "flagged": True,
                "reason": "jailbreak_regex",
                "risk_score": 0.95,
                "suggested_rewrite": "Я не могу выполнить этот запрос."
            }

    # ☠️ 2. Проверка токсичности
    toxic_count = sum(1 for w in TOXIC_KEYWORDS if contains_word(cleaned, w))
    if toxic_count >= 1:
        risk = min(0.7 + toxic_count * 0.1, 0.9)
        return {
            "flagged": True,
            "reason": "toxic_content",
            "risk_score": round(risk, 2),
            "suggested_rewrite": "Пожалуйста, общайтесь уважительно."
        }

    # 🕵️ 3. Проверка утечки ПДн
    pdi_count = sum(1 for w in PDI_KEYWORDS if contains_word(cleaned, w))
    if pdi_count >= 1:
        return {
            "flagged": True,
            "reason": "pdi_leak",
            "risk_score": 0.9,
            "suggested_rewrite": "Запрос содержит персональные данные. Он заблокирован в целях безопасности."
        }

    # 🚫 4. Запрещённые темы
    for category, words in BANNED_TOPICS.items():
        if any(contains_word(cleaned, w) for w in words):
            risk = 0.85 if category in ["violence", "drugs"] else 0.75
            return {
                "flagged": True,
                "reason": f"harmful_content_{category}",
                "risk_score": risk,
                "suggested_rewrite": "Эта тема выходит за рамки моих возможностей."
            }

    # 📊 5. TF-IDF + классификатор (для сложных jailbreak-атак)
    try:
        X = vectorizer.transform([cleaned])
        prob = classifier.predict_proba(X)[0][1]
        if prob > 0.85:  # повышенный порог для снижения ложных срабатываний
            return {
                "flagged": True,
                "reason": "jailbreak_tfidf",
                "risk_score": round(float(prob), 2),
                "suggested_rewrite": "Запрос заблокирован системой безопасности."
            }
    except Exception as e:
        print(f"Ошибка в ML-модели: {e}")
        pass

    # ✅ Безопасно
    return {
        "flagged": False,
        "reason": "safe",
        "risk_score": 0.0,
        "suggested_rewrite": prompt
    }
