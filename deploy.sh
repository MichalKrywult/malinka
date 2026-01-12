echo "--- Budowanie obrazu ---"
docker build -t discord-bot .

echo "--- Usuwanie starego kontenera ---"
docker rm -f moj_bot || true

echo "--- Uruchamianie bota ---"
docker run -d \
  --name moj_bot \
  --restart unless-stopped \
  -v $(pwd)/discord_bot/data:/app/discord_bot/data \
  discord-bot

echo "--- Gotowe! Logi: ---"
docker logs -f moj_bot