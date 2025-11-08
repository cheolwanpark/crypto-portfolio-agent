# Crypto Portfolio Risk Advisor Agent

AI-powered crypto portfolio risk analysis and advisory service using Claude SDK and FastAPI.

## Features

- **Conversational AI Agent**: Natural language interaction for portfolio advice
- **Risk-Based Analysis**: No price predictions, focus on risk management
- **Real-time Updates**: Background processing with immediate status visibility
- **Comprehensive Tools**:
  - Historical data analysis (spot, futures, lending)
  - Risk profile calculation (VaR, Sharpe, scenarios)
  - Portfolio recommendations
  - Stress testing

## Architecture

```
FastAPI API (port 8001)
├── 5 REST endpoints
├── Redis (chat storage + real-time updates)
├── RedisQueue (background agent processing)
└── Claude AI Agent with 3 tools
    ├── HistoricalDataTool (backend API wrapper)
    ├── RiskProfileTool (backend API wrapper)
    └── PortfolioTool (portfolio management)
```

## Quick Start

### Prerequisites

- Python 3.11+
- Redis
- Backend API running on port 8000
- Anthropic API key

### Local Development

1. **Install dependencies**:

```bash
pip install -e .
```

2. **Configure environment**:

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

3. **Start Redis**:

```bash
docker-compose up redis -d
```

4. **Start the API**:

```bash
python -m uvicorn src.server:app --host 0.0.0.0 --port 8001 --reload
```

5. **Start worker(s)** (in separate terminal):

```bash
rq worker chat-agent --with-scheduler
```

### Docker Deployment

```bash
# Set environment variable
export ANTHROPIC_API_KEY=sk-ant-...

# Start all services
docker-compose up -d

# Scale workers
docker-compose up -d --scale agent-worker=3
```

## API Endpoints

### POST /chat
Create a new chat and start agent processing.

**Request**:
```json
{
  "user_prompt": "Build me a conservative portfolio with max 15% drawdown",
  "strategy": "Conservative",
  "target_apy": 20.0,
  "max_drawdown": 15.0
}
```

**Response**: `202 Accepted` with chat record

### GET /chat
List all chats (newest first).

**Query params**:
- `limit` (default: 50, max: 100)
- `offset` (default: 0)

### GET /chat/{id}
Get chat with full message history.

**Response**:
```json
{
  "id": "abc123",
  "status": "completed",
  "strategy": "Conservative",
  "target_apy": 20.0,
  "max_drawdown": 15.0,
  "messages": [
    {
      "type": "user",
      "message": "Build me a conservative portfolio...",
      "timestamp": "2025-01-01T00:00:00Z"
    },
    {
      "type": "agent",
      "message": "I'll help you build a conservative portfolio...",
      "reasonings": ["Choosing 60% BTC because..."],
      "timestamp": "2025-01-01T00:00:30Z"
    }
  ],
  "portfolio": [
    {
      "asset": "BTC",
      "quantity": 0.5,
      "position_type": "spot",
      "entry_price": 45000.0,
      "leverage": 1.0
    }
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:30Z"
}
```

### GET /chat/{id}/portfolio
Get current portfolio for a chat.

### POST /chat/{id}/followup
Continue conversation with a followup message.

**Request**:
```json
{
  "prompt": "What if I want more exposure to ETH?"
}
```

## Configuration

Environment variables (see `.env.example`):

- `ANTHROPIC_API_KEY`: Claude API key (required)
- `BACKEND_API_URL`: Backend API URL (default: `http://localhost:8000`)
- `REDIS_URL`: Redis connection string (default: `redis://127.0.0.1:6379/0`)
- `QUEUE_NAME`: RQ queue name (default: `chat-agent`)
- `MAX_WORKERS`: Max concurrent workers (default: 10)
- `AGENT_MAX_TURNS`: Max conversation turns (default: 15)
- `AGENT_TIMEOUT_SECONDS`: Agent execution timeout (default: 60)
- `AGENT_MAX_TOOL_CALLS`: Max tool calls per execution (default: 30)

## Agent Behavior

The agent:
1. Analyzes user requirements (strategy, target APY, max drawdown)
2. Gathers historical market data using `get_aggregated_stats`
3. Analyzes potential portfolios using `calculate_risk_profile`
4. Recommends positions using `set_portfolio`
5. Provides educational explanations about risk/return trade-offs

## Status Flow

```
queued → processing → completed/failed/timeout
```

- **queued**: Job enqueued, waiting for worker
- **processing**: Agent actively working
- **completed**: Successfully generated response
- **failed**: Error occurred (see `error_message`)
- **timeout**: Exceeded execution time limit

## Development

### Project Structure

```
agent/
├── src/
│   ├── api/          # FastAPI routes & service layer
│   ├── agent/        # AI agent & tools
│   ├── storage/      # Redis storage
│   ├── queue/        # Background queue
│   ├── models.py     # Pydantic models
│   ├── config.py     # Settings
│   └── server.py     # FastAPI app
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

### Running Tests

```bash
pytest tests/
```

## Troubleshooting

### Agent Times Out

- Increase `AGENT_TIMEOUT_SECONDS`
- Check backend API response times
- Verify Claude API is accessible

### Redis Connection Errors

- Ensure Redis is running: `docker-compose ps redis`
- Check `REDIS_URL` configuration

### Worker Not Processing Jobs

- Check worker logs: `docker-compose logs agent-worker`
- Verify `ANTHROPIC_API_KEY` is set
- Ensure backend API is accessible from worker

## License

MIT
