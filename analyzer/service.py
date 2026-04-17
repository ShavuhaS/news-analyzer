import spacy
from typing import Dict, Any, List
import logging
from config import settings
from analyzer.geocoders import GeoNamesUK
from senticnet import senticnet

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    # Словник для виправлення проблемних абревіатур
    LOCATION_ALIASES = {
        "сша": "сполучені штати америки",
        "рф": "росія",
        "єс": "європейський союз",
        "оон": "організація об'єднаних націй",
        "зсу": "україна", 
    }
    KNOWN_LOCATION_ERRORS = {
        'кий': 'київ',
    }

    # Слова-підсилювачі емоцій
    INTENSIFIERS = {"дуже", "надзвичайно", "вкрай", "абсолютно", "вельми", "занадто"}
    # Частки заперечення
    NEGATIONS = {"не", "ні", "ані"}

    def __init__(self):
        if settings.USE_GPU:
            try:
                is_gpu = spacy.prefer_gpu()
                if is_gpu:
                    logger.info("GPU support enabled for spaCy")
                else:
                    logger.warning("GPU was requested but not available. Using CPU.")
            except Exception as e:
                logger.error(f"Failed to enable GPU: {e}. Falling back to CPU.")
        
        try:
            self.nlp = spacy.load(settings.SPACY_MODEL)
            logger.info(f"Loaded spaCy model: {settings.SPACY_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise

        self.geocoder = GeoNamesUK(username=settings.GEONAMES_USERNAME)

    def analyze(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проводить повний аналіз новини: NER, Sentiment, Classification.
        """
        title = item.get('title', '')
        description = item.get('description', '')
        
        # Об'єднаний текст для NER та класифікації
        text = f"{title}\n{description}"
        doc = self.nlp(text)
        
        # 1. Знаходження локацій (NER + Geocoding)
        locations = self._get_locations(doc)
        
        # 2. Сентимент-аналіз (з урахуванням ваги заголовка)
        sentiment_score = self._analyze_sentiment(title, description)
        
        # 3. Категоризація (класифікація)
        category = self._classify_category(doc)
        
        return {
            **item,
            "locations": locations,
            "sentiment_score": sentiment_score,
            "category": category,
        }

    def _get_locations(self, doc) -> List[Dict[str, Any]]:
        """
        Визначає локації в тексті, лематизує їх та геокодує через GeoNames.
        Використовує словник абревіатур для покращення точності.
        """
        locations = []
        processed_lemmas = set()

        for ent in doc.ents:
            if ent.label_ in ("LOC", "GPE"):
                original_text = ent.text
                lemma = ent.lemma_.lower().strip()
                lemma = self.KNOWN_LOCATION_ERRORS.get(lemma, lemma)

                search_query = self.LOCATION_ALIASES.get(lemma, lemma)

                if search_query in processed_lemmas:
                    continue
                
                try:
                    location = self.geocoder.geocode(search_query)
                    if location:
                        locations.append({
                            "original_text": original_text,
                            "lemma": lemma,
                            "formatted_address": location.address,
                            "lat": location.latitude,
                            "lon": location.longitude
                        })
                        processed_lemmas.add(search_query)
                except Exception as e:
                    logger.error(f"Geocoding error for '{search_query}': {e}")
        
        return locations

    def _process_tokens_for_sentiment(self, doc, weight_multiplier: float) -> tuple[float, float]:
        """
        Обробляє токени документа, повертає сумарну полярність та сумарну вагу знайдених слів.
        """
        polarity_sum = 0.0
        weight_sum = 0.0
        allowed_pos = {"ADJ", "VERB", "ADV", "NOUN"}

        for token in doc:
            if token.is_stop or token.is_punct or token.pos_ not in allowed_pos or token.ent_type_:
                continue

            lemma = token.lemma_.lower().strip()

            if lemma in senticnet:
                base_polarity = float(senticnet[lemma][7])
                
                modifier = 1.0
                for child in token.children:
                    child_lemma = child.lemma_.lower().strip()
                    
                    if child_lemma in self.NEGATIONS and child.dep_ in ("advmod", "neg"):
                        modifier *= -1.0
                    elif child_lemma in self.INTENSIFIERS and child.dep_ == "advmod":
                        modifier *= 1.25

                final_polarity = base_polarity * modifier * weight_multiplier
                
                polarity_sum += final_polarity
                weight_sum += weight_multiplier

        return polarity_sum, weight_sum

    def _analyze_sentiment(self, title: str, description: str) -> float:
        """
        Обчислює загальний сентимент новини. Заголовок має більшу вагу.
        """
        total_polarity = 0.0
        total_weight = 0.0

        if title:
            title_doc = self.nlp(title)
            p_sum, w_sum = self._process_tokens_for_sentiment(title_doc, weight_multiplier=1.5)
            total_polarity += p_sum
            total_weight += w_sum

        if description:
            desc_doc = self.nlp(description)
            p_sum, w_sum = self._process_tokens_for_sentiment(desc_doc, weight_multiplier=1.0)
            total_polarity += p_sum
            total_weight += w_sum

        if total_weight == 0:
            return 0.0

        average_polarity = total_polarity / total_weight
        
        # Обмежуємо значення діапазоном [-1.0, 1.0]
        average_polarity = max(-1.0, min(1.0, average_polarity))

        return round(average_polarity, 3)

    def _classify_category(self, doc) -> str:
        # TODO: Додати навчену модель (Naive Bayes)
        return "Загальні"
