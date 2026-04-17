FROM nvidia/cuda:13.0.3-runtime-ubuntu24.04

# Встановлюємо Python та pip
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо залежності через системний pip (з прапорцем для Ubuntu 24.04)
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Завантажуємо трансформер-модель для української мови
RUN python3.12 -m spacy download uk_core_news_trf

# Копіюємо вихідний код
COPY . .

# Шляхи для CUDA
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

CMD ["python3.12", "main.py"]
