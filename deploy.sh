echo "--- Budowanie obrazu ---"
docker build -t discord-bot .

echo "--- Usuwanie starego kontenera ---"
docker rm -f moj_bot || true

echo "--- Uruchamianie bota ---"
docker run -d \
  --name moj_bot \
  --restart unless-stopped \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  -v $(pwd)/discord_bot/data:/app/discord_bot/data \
  discord-bot
docker image prune -f
echo "--- Gotowe! Logi: ---"
docker logs -f moj_bot