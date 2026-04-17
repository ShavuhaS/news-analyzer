import spacy
from typing import Dict, Any, List
import logging
from config import settings

logger = logging.getLogger(__name__)

class NewsAnalyzer:
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

    def analyze(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проводить повний аналіз новини: NER, Sentiment, Classification.
        """
        text = f"{item.get('title', '')}\n{item.get('description', '')}"
        doc = self.nlp(text)
        
        # 1. Знаходження локацій (NER)
        locations = list(set([ent.text for ent in doc.ents if ent.label_ in ("LOC", "GPE")]))
        
        # 2. Сентимент-аналіз (згідно з ТЗ на базі SenticNet)
        sentiment_score = self._analyze_sentiment(doc)
        
        # 3. Категоризація (класифікація)
        category = self._classify_category(doc)
        
        return {
            **item,
            "locations": locations,
            "sentiment_score": sentiment_score,
            "category": category,
            "is_analyzed": True
        }

    def _get_locations(self, doc) -> list[str]:
        # TODO: Написати логіку знаходження географічних локацій у тексті
        return []

    def _analyze_sentiment(self, doc) -> float:
        # TODO: Інтегрувати SenticNet
        return 0.0

    def _classify_category(self, doc) -> str:
        # TODO: Додати навчену модель (Naive Bayes)
        return "Загальні"
