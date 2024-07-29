FROM python:slim

WORKDIR /app
COPY requirements.lock ./
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.lock
ENV PORT=8080

COPY src .
CMD gunicorn -w 4 main:app -b :$PORT
