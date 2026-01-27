cd /opt/qiq
cat > deploy.sh << 'EOF'
#!/bin/bash
set -e
cd /opt/qiq
echo "Pulling latest from GitHub..."
git pull origin build-2.2
echo "Building Docker image..."
docker build -t qiq .
echo "Stopping old container..."
docker stop qiq || true
docker rm qiq || true
echo "Starting new container..."
docker run -d --name qiq -p 80:8000 --restart unless-stopped qiq
echo "Deployment complete. Verifying..."
sleep 2
docker exec qiq grep -q "formatChoiceLabel" /app/index.html && echo "✓ File verified in container" || echo "✗ File NOT in container"
curl -s http://127.0.0.1:8000/ | grep -q "formatChoiceLabel" && echo "✓ Being served correctly" || echo "✗ NOT being served"
EOF

chmod +x deploy.sh