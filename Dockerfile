FROM python:3.11-slim

WORKDIR /app

COPY main.py /app/main.py
COPY RAG /app/RAG
COPY frontend /app/frontend
COPY Embedding /app/Embedding

EXPOSE 8000

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
