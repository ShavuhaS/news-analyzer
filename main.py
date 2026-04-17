import json
import logging
import sys
from confluent_kafka import Consumer, Producer, KafkaError
from config import settings
from analyzer.service import NewsAnalyzer
from analyzer.geocoders import GeoNamesUK

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("news-analyzer")

def main():
    logger.info("Starting News Analyzer service...")
    
    # 1. Ініціалізація аналізатора (завантаження моделі на GPU)
    try:
        analyzer = NewsAnalyzer()
    except Exception as e:
        logger.critical(f"Failed to initialize analyzer: {e}")
        sys.exit(1)

    # 2. Налаштування Kafka Consumer
    conf = {
        'bootstrap.servers': settings.KAFKA_BROKERS,
        'group.id': settings.KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest'
    }
    
    consumer = Consumer(conf)
    consumer.subscribe([settings.KAFKA_NEWS_TOPIC])

    # 3. Налаштування Kafka Producer (для відправки проаналізованих новин)
    producer = Producer({'bootstrap.servers': settings.KAFKA_BROKERS})

    def delivery_report(err, msg):
        """ Викликається після відправки повідомлення в Kafka. """
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.debug(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    logger.info(f"Subscribed to topic: {settings.KAFKA_NEWS_TOPIC}")
    
    try:
        while True:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"Kafka error: {msg.error()}")
                    break

            # 4. Обробка повідомлення
            try:
                # Десеріалізація JSON
                item = json.loads(msg.value().decode('utf-8'))
                
                # Аналіз
                analyzed_item = analyzer.analyze(item)
                
                # Відправка результату в новий топік
                producer.produce(
                    settings.KAFKA_ANALYZED_TOPIC,
                    key=msg.key(),
                    value=json.dumps(analyzed_item, ensure_ascii=False).encode('utf-8'),
                    callback=delivery_report
                )
                
                # Producer.produce працює асинхронно, викликаємо poll для обробки колбеків
                producer.poll(0)
                
                logger.info(f"Analyzed item: {item.get('title', 'No Title')}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
            except Exception as e:
                logger.error(f"Error during analysis: {e}", exc_info=True)

    except KeyboardInterrupt:
        logger.info("Stopping service...")
    finally:
        # Закриваємо з'єднання
        consumer.close()
        producer.flush()

if __name__ == "__main__":
    main()
