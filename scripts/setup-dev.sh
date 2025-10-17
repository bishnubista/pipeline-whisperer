#!/bin/bash
# Development environment setup script

set -e

echo "🔧 Setting up Pipeline Whisperer development environment..."

cd "$(dirname "$0")/.."

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Aborting." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Aborting." >&2; exit 1; }

echo "✅ Prerequisites check passed"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
  echo "Creating .env file from template..."
  cp .env.example .env
  echo "⚠️  Please edit .env and add your API keys before running the application"
fi

# Setup Python virtual environment
echo ""
echo "Setting up Python environment..."
cd apps/agent-api
if [ ! -d venv ]; then
  python3 -m venv venv
  echo "✅ Python virtual environment created"
fi

source venv/bin/activate
pip install -r requirements.txt
echo "✅ Python dependencies installed"
cd ../..

# Setup Node.js dependencies
echo ""
echo "Setting up Node.js environment..."
cd apps/web
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
else
  npm install
fi
echo "✅ Node.js dependencies installed"
cd ../..

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Start infrastructure: ./scripts/start-infra.sh"
echo "  3. Start API: cd apps/agent-api && source venv/bin/activate && python main.py"
echo "  4. Start web: cd apps/web && pnpm dev (or npm run dev)"
