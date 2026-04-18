import json
import logging
import sys
import time
from confluent_kafka import Consumer, Producer, KafkaError
from config import settings
from analyzer.service import NewsAnalyzer

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("news-analyzer")

def main():
    logger.info("Starting News Analyzer service...")
    
    # 1. Ініціалізація аналізатора
    try:
        analyzer = NewsAnalyzer()
    except Exception as e:
        logger.critical(f"Failed to initialize analyzer: {e}")
        sys.exit(1)

    # 2. Налаштування Kafka Consumer
    conf = {
        'bootstrap.servers': settings.KAFKA_BROKERS,
        'group.id': settings.KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True
    }
    
    consumer = Consumer(conf)
    consumer.subscribe([settings.KAFKA_NEWS_TOPIC])

    # 3. Налаштування Kafka Producer
    producer = Producer({'bootstrap.servers': settings.KAFKA_BROKERS})

    def delivery_report(err, msg):
        if err is not None:
            logger.error(f'Message delivery failed: {err}')

    logger.info(f"Subscribed to topic: {settings.KAFKA_NEWS_TOPIC}")
    
    processed_count = 0
    last_log_time = time.time()

    try:
        while True:
            msg = consumer.poll(0.1)
            
            # Періодичне логування статистики
            current_time = time.time()
            if current_time - last_log_time >= settings.LOG_INTERVAL_SEC:
                cache_stats = analyzer.geocoder.geocode.cache_info()
                logger.info(
                    f"=== Стан сервісу ===\n"
                    f"Проаналізовано новин: {processed_count}\n"
                    f"Кеш геокодера: Hits={cache_stats.hits}, Misses={cache_stats.misses}, Size={cache_stats.currsize}/{cache_stats.maxsize}\n"
                    f"====================="
                )
                last_log_time = current_time

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
                item = json.loads(msg.value().decode('utf-8'))
                
                analyzed_item = analyzer.analyze(item)
                
                producer.produce(
                    settings.KAFKA_ANALYZED_TOPIC,
                    key=msg.key(),
                    value=json.dumps(analyzed_item, ensure_ascii=False).encode('utf-8'),
                    callback=delivery_report
                )
                
                producer.poll(0)
                processed_count += 1
                logger.debug(f"Analyzed: {item.get('title', 'No Title')}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
            except Exception as e:
                logger.error(f"Error during analysis: {e}", exc_info=True)

    except KeyboardInterrupt:
        logger.info("Stopping service...")
    finally:
        consumer.close()
        producer.flush()

if __name__ == "__main__":
    main()
