# Agent API Documentation

This document describes the API structure for the crypto portfolio agent service.

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. List Chats

**Endpoint:** `GET /chat`

**Description:** Retrieves a list of all chat sessions.

**Response Schema:**
```json
[
  {
    "id": "string (UUID)",
    "status": "processing | completed | failed",
    "strategy": "Conservative | Balanced | Aggressive",
    "target_apy": "number",
    "max_drawdown": "number",
    "has_portfolio": "boolean",
    "message_count": "number",
    "created_at": "string (ISO 8601 datetime)",
    "updated_at": "string (ISO 8601 datetime)"
  }
]
```

**Example Response:**
```json
[
  {
    "id": "df2c43d7adca4cd2b9cee60efa737829",
    "status": "processing",
    "strategy": "Conservative",
    "target_apy": 20,
    "max_drawdown": 15,
    "has_portfolio": false,
    "message_count": 1,
    "created_at": "2025-11-08T20:47:52.542442",
    "updated_at": "2025-11-08T20:47:52.752607"
  }
]
```

---

### 2. Get Chat Details

**Endpoint:** `GET /chat/{id}`

**Description:** Retrieves detailed information about a specific chat session, including all messages, reasoning steps, and tool calls.

**Path Parameters:**
- `id` (string, required): The UUID of the chat session

**Response Schema:**
```json
{
  "id": "string (UUID)",
  "status": "processing | completed | failed",
  "strategy": "Conservative | Balanced | Aggressive",
  "target_apy": "number",
  "max_drawdown": "number",
  "messages": [
    {
      "type": "user | agent",
      "message": "string",
      "reasonings": [
        {
          "summary": "string",
          "detail": "string",
          "timestamp": "string (ISO 8601 datetime)"
        }
      ],
      "toolcalls": [
        {
          "tool_name": "string",
          "message": "string",
          "timestamp": "string (ISO 8601 datetime)",
          "inputs": "object",
          "outputs": "object",
          "status": "success | error"
        }
      ],
      "timestamp": "string (ISO 8601 datetime)"
    }
  ],
  "portfolio": "object | null",
  "portfolio_versions": "array",
  "error_message": "string | null",
  "created_at": "string (ISO 8601 datetime)",
  "updated_at": "string (ISO 8601 datetime)"
}
```

**Message Types:**

#### User Message
```json
{
  "type": "user",
  "message": "메이저한 코인들만 써서 구성해줘",
  "reasonings": [],
  "toolcalls": [],
  "timestamp": "2025-11-08T20:47:52.546722"
}
```

#### Agent Message
```json
{
  "type": "agent",
  "message": "[Agent is thinking...]",
  "reasonings": [
    {
      "summary": "Phase 1 완료: 투자자 프로필 및 정책 분석",
      "detail": "...",
      "timestamp": "2025-11-08T20:48:11.739766"
    }
  ],
  "toolcalls": [
    {
      "tool_name": "get_aggregated_stats",
      "message": "[tool] searching BTC, ETH, SOL",
      "timestamp": "2025-11-08T20:48:39.825201",
      "inputs": {
        "assets": ["BTC", "ETH", "SOL"],
        "start_date": "2024-05-10T00:00:00Z",
        "end_date": "2025-01-08T00:00:00Z",
        "data_types": ["spot"]
      },
      "outputs": {
        "query": { ... },
        "data": { ... },
        "correlations": { ... },
        "warnings": null,
        "timestamp": "2025-11-08T20:48:39.824176Z"
      },
      "status": "success"
    }
  ],
  "timestamp": "2025-11-08T20:48:11.740599"
}
```

---

### 3. Get Chat Portfolio

**Endpoint:** `GET /chat/{id}/portfolio`

**Description:** Retrieves the portfolio information for a specific chat session, including all versions and the latest portfolio.

**Path Parameters:**
- `id` (string, required): The UUID of the chat session

**Response Schema:**
```json
{
  "chat_id": "string (UUID)",
  "portfolio_versions": [
    {
      "version": "number",
      "positions": [
        {
          "asset": "string",
          "quantity": "number",
          "position_type": "spot | futures | lending_supply | lending_borrow",
          "entry_price": "number",
          "leverage": "number",
          "entry_timestamp": "string (ISO 8601 datetime) | null",
          "entry_index": "number | null",
          "borrow_type": "variable | stable | null"
        }
      ],
      "explanation": "string",
      "timestamp": "string (ISO 8601 datetime)"
    }
  ],
  "latest_portfolio": [
    {
      "asset": "string",
      "quantity": "number",
      "position_type": "spot | futures | lending_supply | lending_borrow",
      "entry_price": "number",
      "leverage": "number",
      "entry_timestamp": "string (ISO 8601 datetime) | null",
      "entry_index": "number | null",
      "borrow_type": "variable | stable | null"
    }
  ],
  "has_portfolio": "boolean"
}
```

**Position Types:**
- `spot`: Spot position
- `futures`: Futures position (with leverage)
- `lending_supply`: Lending supply position (providing liquidity)
- `lending_borrow`: Lending borrow position (borrowing assets)

**Example Response:**
```json
{
  "chat_id": "df2c43d7adca4cd2b9cee60efa737829",
  "portfolio_versions": [
    {
      "version": 1,
      "positions": [
        {
          "asset": "USDC",
          "quantity": 50000,
          "position_type": "lending_supply",
          "entry_price": 1,
          "leverage": 1,
          "entry_timestamp": "2025-01-01T00:00:00Z",
          "entry_index": null,
          "borrow_type": null
        },
        {
          "asset": "BTC",
          "quantity": 0.3154,
          "position_type": "spot",
          "entry_price": 95134.92,
          "leverage": 1,
          "entry_timestamp": null,
          "entry_index": null,
          "borrow_type": null
        },
        {
          "asset": "ETH",
          "quantity": 4.478,
          "position_type": "spot",
          "entry_price": 3349.79,
          "leverage": 1,
          "entry_timestamp": null,
          "entry_index": null,
          "borrow_type": null
        },
        {
          "asset": "SOL",
          "quantity": 25.58,
          "position_type": "spot",
          "entry_price": 195.5,
          "leverage": 1,
          "entry_timestamp": null,
          "entry_index": null,
          "borrow_type": null
        }
      ],
      "explanation": "보수적 전략과 목표 수익률 20% APY, 최대 손실 15%를 모두 충족하는 최적의 포트폴리오입니다...",
      "timestamp": "2025-11-08T20:52:45.748490"
    }
  ],
  "latest_portfolio": [
    {
      "asset": "USDC",
      "quantity": 50000,
      "position_type": "lending_supply",
      "entry_price": 1,
      "leverage": 1,
      "entry_timestamp": "2025-01-01T00:00:00Z",
      "entry_index": null,
      "borrow_type": null
    },
    {
      "asset": "BTC",
      "quantity": 0.3154,
      "position_type": "spot",
      "entry_price": 95134.92,
      "leverage": 1,
      "entry_timestamp": null,
      "entry_index": null,
      "borrow_type": null
    },
    {
      "asset": "ETH",
      "quantity": 4.478,
      "position_type": "spot",
      "entry_price": 3349.79,
      "leverage": 1,
      "entry_timestamp": null,
      "entry_index": null,
      "borrow_type": null
    },
    {
      "asset": "SOL",
      "quantity": 25.58,
      "position_type": "spot",
      "entry_price": 195.5,
      "leverage": 1,
      "entry_timestamp": null,
      "entry_index": null,
      "borrow_type": null
    }
  ],
  "has_portfolio": true
}
```

---

## Common Data Types

### Investment Strategy
- `Conservative`: Low risk, stability focused
- `Balanced`: Medium risk/reward balance
- `Aggressive`: High risk, maximum returns

### Position Type
- `spot`: Direct asset ownership
- `futures`: Leveraged futures position
- `lending_supply`: Asset supplied to lending protocol
- `lending_borrow`: Asset borrowed from lending protocol

### Borrow Type (for lending_borrow positions)
- `variable`: Variable interest rate
- `stable`: Stable interest rate
- `null`: Not applicable (for non-borrow positions)

### Chat Status
- `processing`: Agent is currently working on the request
- `completed`: Request has been completed successfully
- `failed`: Request has failed with an error

---

## Notes

1. All timestamps are in ISO 8601 format (e.g., `2025-11-08T20:47:52.542442`)
2. UUIDs are used for chat session IDs
3. The `has_portfolio` field indicates whether a portfolio has been generated for the chat
4. `portfolio_versions` tracks all historical versions of the portfolio as it evolves
5. `latest_portfolio` is a convenience field that duplicates the most recent portfolio version
6. Tool call inputs/outputs vary by tool type - see individual tool documentation for details
7. Reasoning steps track the agent's thought process through different phases of analysis
