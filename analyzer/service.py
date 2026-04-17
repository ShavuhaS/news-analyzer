import spacy
from typing import Dict, Any, List
import logging
from config import settings
from analyzer.geocoders import GeoNamesUK

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    # Словник для виправлення проблемних абревіатур
    LOCATION_ALIASES = {
        "сша": "сполучені штати америки",
        "рф": "росія",
        "зсу": "україна", 
    }

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
        text = f"{item.get('title', '')}\n{item.get('description', '')}"
        doc = self.nlp(text)
        
        # 1. Знаходження локацій (NER + Geocoding)
        locations = self._get_locations(doc)
        
        # 2. Сентимент-аналіз (згідно з ТЗ на базі SenticNet)
        sentiment_score = self._analyze_sentiment(doc)
        
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

    def _analyze_sentiment(self, doc) -> float:
        # TODO: Інтегрувати SenticNet
        return 0.0

    def _classify_category(self, doc) -> str:
        # TODO: Додати навчену модель (Naive Bayes)
        return "Загальні"
