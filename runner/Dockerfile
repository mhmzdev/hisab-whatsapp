FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends hledger && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
COPY runner/requirements.txt runner-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r runner-requirements.txt
COPY hisab ./hisab
COPY templates ./templates
COPY runner ./runner
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "runner.main"]
