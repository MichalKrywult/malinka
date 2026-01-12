FROM python:3.13-slim

WORKDIR /app

COPY discord_bot/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY discord_bot/ ./discord_bot/

CMD ["python", "discord_bot/main.py"]