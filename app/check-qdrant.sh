#!/bin/bash
if ss -tuln | grep -q ':6333 '; then
    echo "✅ Qdrant работает"
    curl -s http://localhost:6333/health | jq .
else
    echo "❌ Qdrant не запущен"
fi