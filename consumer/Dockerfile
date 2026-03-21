FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/main.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
