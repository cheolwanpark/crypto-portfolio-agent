# Graph API Implementation Summary

## Overview

Successfully implemented a new `/api/v1/analysis/graph` endpoint that provides chart-ready visualization data for portfolio risk dashboards supporting spot, futures (perp), and lending positions.

## What Was Implemented

### Phase 1 - Core Graph Types (✅ Completed)

#### 1. Portfolio Value Sensitivity Heatmap (`sensitivity`)
**Purpose**: Visualize how portfolio value changes with underlying asset price movements

**Use Case**: Shows "if BTC drops 20%, my portfolio is worth X"

**Data Structure**:
```json
{
  "data_points": [
    {"x": -30.0, "y": 70000, "return_pct": -30.0, "pnl": -30000},
    {"x": -20.0, "y": 80000, "return_pct": -20.0, "pnl": -20000},
    ...
    {"x": 0.0, "y": 100000, "return_pct": 0.0, "pnl": 0},
    ...
    {"x": 30.0, "y": 130000, "return_pct": 30.0, "pnl": 30000}
  ],
  "current_position": 3,
  "value_range": {"min": 70000, "max": 130000, "current": 100000}
}
```

**Recommended Visualization**: Line chart with shaded area, vertical line at x=0

---

#### 2. Delta Gauge Chart (`delta`)
**Purpose**: Monitor market neutrality in real-time

**Use Case**: For delta-neutral strategies (spot + short perp hedging), shows if portfolio is balanced

**Data Structure**:
```json
{
  "delta_raw": 150.5,
  "delta_normalized": 0.015,
  "status": "neutral",
  "portfolio_value": 100000,
  "directional_exposure_pct": 0.15
}
```

**Status Levels**:
- `neutral` (-0.05 to +0.05): Green zone
- `slight_long/slight_short` (0.05 to 0.2): Yellow zone
- `high_long/high_short` (>0.2): Red zone

**Recommended Visualization**: Semi-circular gauge chart with color zones

---

#### 3. Risk Contribution Breakdown (`risk_contribution`)
**Purpose**: Show which assets contribute most to portfolio risk

**Use Case**: "BTC contributes 60% of my portfolio value but 75% of risk" → rebalancing needed

**Data Structure**:
```json
{
  "contributions": [
    {
      "asset": "BTC",
      "risk_pct": 75.2,
      "value_pct": 60.0,
      "risk_value": 0.012,
      "position_value": 60000
    },
    {
      "asset": "ETH",
      "risk_pct": 24.8,
      "value_pct": 40.0,
      "risk_value": 0.004,
      "position_value": 40000
    }
  ],
  "total_risk": 0.016,
  "diversification_benefit": 12.5
}
```

**Formula Used**: Marginal Contribution to Risk (MCR)
```
Risk_Contribution_i = (w_i × Cov(R_i, R_p)) / σ_p
```

**Recommended Visualization**: Pie chart or stacked bar chart

---

#### 4. Risk Alert Dashboard (`alerts`)
**Purpose**: Real-time risk monitoring with health scores

**Use Case**: "Health score is 65/100, volatility warning, rebalancing recommended"

**Data Structure**:
```json
{
  "health_score": 76,
  "health_components": {
    "delta_neutral": {"score": 25, "status": "excellent"},
    "volatility": {"score": 15, "status": "good"},
    "sharpe_ratio": {"score": 18, "status": "good"},
    "leverage": {"score": 18, "status": "good"}
  },
  "liquidation_risk": {
    "overall_risk": "moderate",
    "positions": [
      {
        "asset": "BTC",
        "position_type": "futures_short",
        "liquidation_price": 105000,
        "current_price": 96000,
        "price_distance_pct": 48.5,
        "risk_level": "safe"
      }
    ]
  },
  "rebalancing_signal": {
    "needed": false,
    "urgency": "none",
    "current_delta": 150.5,
    "delta_normalized": 0.015
  }
}
```

**Health Score Breakdown** (0-100):
- Delta Neutrality: 25 points
- Volatility: 25 points
- Sharpe Ratio: 25 points
- Leverage Safety: 25 points

**Recommended Visualization**: Card dashboard with color-coded indicators

---

### Phase 2 - Advanced Graphs (🔄 Planned)

#### 5. Funding P&L Waterfall (`funding_waterfall`)
**Purpose**: Decompose P&L into components (spot, perp, funding, lending)

**Status**: Placeholder implemented, calculation logic pending

---

#### 6. Rolling Risk Metrics (`rolling_metrics`)
**Purpose**: Time series of volatility, VaR, Sharpe ratio over time

**Status**: Placeholder implemented, computationally expensive - needs caching

---

#### 7. Monte Carlo Fan Chart (`monte_carlo`)
**Purpose**: Probability distribution of future portfolio values

**Status**: Placeholder implemented, requires simulation engine

---

## API Usage

### Endpoint
```
POST /api/v1/analysis/graph
```

### Request Example
```json
{
  "positions": [
    {
      "asset": "BTC",
      "quantity": 1.0,
      "position_type": "spot",
      "entry_price": 95000
    },
    {
      "asset": "BTC",
      "quantity": -0.95,
      "position_type": "futures_short",
      "entry_price": 95500,
      "leverage": 3
    }
  ],
  "lookback_days": 30,
  "graph_types": ["sensitivity", "delta", "risk_contribution", "alerts"]
}
```

### Response Example
```json
{
  "sensitivity": { /* SensitivityGraphData */ },
  "delta": { /* DeltaGaugeData */ },
  "risk_contribution": { /* RiskContributionData */ },
  "alerts": { /* AlertDashboardData */ },
  "funding_waterfall": null,
  "rolling_metrics": null,
  "monte_carlo": null,
  "metadata": {
    "lookback_days_used": 30,
    "graph_types_generated": ["sensitivity", "delta", "risk_contribution", "alerts"],
    "timestamp": "2025-11-09T08:50:00Z"
  }
}
```

### Supported Position Types
- **Spot**: `"position_type": "spot"`
- **Futures Long**: `"position_type": "futures_long"`
- **Futures Short**: `"position_type": "futures_short"`
- **Lending Supply**: `"position_type": "lending_supply"` (requires `entry_timestamp`)
- **Lending Borrow**: `"position_type": "lending_borrow"` (requires `entry_timestamp`, `borrow_type`)

### Performance Tips
1. **Request only needed graphs** - Each graph type incurs calculation overhead
2. **Use appropriate lookback periods** - 30 days is optimal, 7-90 days supported
3. **Cache results** - Graph data changes slowly, consider caching on client side
4. **Phase 2 graphs are expensive** - `rolling_metrics` and `monte_carlo` require significant computation

---

## Files Created/Modified

### New Files
1. `/backend/src/analysis/graph.py` (500+ lines)
   - Core calculation functions for all graph types
   - Phase 1 fully implemented
   - Phase 2 placeholder functions

2. `/backend/test_graph_endpoint.py`
   - Unit tests for all Phase 1 graph calculations
   - All tests passing ✅

### Modified Files
1. `/backend/src/models.py`
   - Added graph request/response models:
     - `GraphRequest`
     - `GraphResponse`
     - `SensitivityGraphData`
     - `DeltaGaugeData`
     - `RiskContributionData`
     - `AlertDashboardData`
     - Supporting models

2. `/backend/src/api.py`
   - Added `POST /api/v1/analysis/graph` endpoint (line 1222)
   - Imports for graph models
   - Full OpenAPI documentation

---

## Testing

All Phase 1 functions tested and passing:

```bash
cd backend
uv run python test_graph_endpoint.py
```

**Test Results**:
```
✅ Sensitivity graph test passed!
✅ Delta gauge test passed!
✅ Risk contribution test passed!
✅ Alert dashboard test passed!
✅ GraphRequest validation test passed!

All tests passed!
```

---

## Graph Recommendations by Use Case

### For Delta-Neutral Strategies (Spot + Short Perp)
**Priority Graphs**:
1. `delta` - Monitor market neutrality
2. `alerts` - Health check + rebalancing signals
3. `sensitivity` - Understand downside risk despite hedge

### For Long-Only Portfolios
**Priority Graphs**:
1. `sensitivity` - Understand price exposure
2. `risk_contribution` - Optimize diversification
3. `alerts` - Risk monitoring

### For Leveraged Positions
**Priority Graphs**:
1. `alerts` - Liquidation risk monitoring (critical!)
2. `delta` - Directional exposure
3. `sensitivity` - Scenario analysis

### For Lending/Borrowing Strategies
**Priority Graphs**:
1. `alerts` - Health factor monitoring
2. `risk_contribution` - Asset allocation
3. (Phase 2) `funding_waterfall` - Interest income/expense breakdown

---

## Frontend Integration Example

```typescript
// Example React hook for fetching graph data
async function fetchGraphData(positions: Position[], graphTypes: string[]) {
  const response = await fetch('/api/v1/analysis/graph', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      positions,
      lookback_days: 30,
      graph_types: graphTypes
    })
  });

  const data = await response.json();

  // Use Recharts, Chart.js, or D3 for visualization
  if (data.sensitivity) {
    renderLineChart(data.sensitivity.data_points);
  }

  if (data.delta) {
    renderGaugeChart(data.delta);
  }

  if (data.risk_contribution) {
    renderPieChart(data.risk_contribution.contributions);
  }

  if (data.alerts) {
    renderDashboard(data.alerts);
  }
}
```

---

## Next Steps (Phase 2)

1. **Funding P&L Waterfall**
   - Implement P&L decomposition logic
   - Aggregate funding payments from historical data
   - Calculate lending interest accrual

2. **Rolling Risk Metrics**
   - Implement rolling window calculations
   - Add caching layer (Redis recommended)
   - Optimize for performance

3. **Monte Carlo Simulation**
   - Implement multivariate normal simulation
   - Use Cholesky decomposition for correlated returns
   - Generate percentile bands (5th, 25th, 50th, 75th, 95th)

4. **Performance Optimization**
   - Add Redis caching for expensive calculations
   - Implement background task queue for monte_carlo
   - Consider WebSocket for real-time updates

---

## Limitations & Considerations

1. **Data Availability**
   - Funding rates: 30 days max (Binance API limitation)
   - Minimum 7 days lookback required for reliable statistics
   - 30 days recommended for stable risk metrics

2. **Calculation Assumptions**
   - Delta calculation assumes linear price sensitivity
   - Liquidation prices are simplified (doesn't account for fees, slippage)
   - Risk contribution uses historical correlations (may not predict future)

3. **Performance**
   - Phase 1 graphs share risk-profile calculation (~2-5 seconds)
   - Phase 2 graphs (rolling, monte_carlo) will be significantly slower
   - Consider async processing + webhooks for Phase 2

---

## Summary

**What Users Get**:
- 4 production-ready graph types for comprehensive risk visualization
- Support for spot, futures (perp), and lending positions
- Real-time risk monitoring with actionable alerts
- Flexible API - request only the graphs you need

**What Frontend Needs to Do**:
- Call `/api/v1/analysis/graph` with portfolio positions
- Render returned data using chart libraries (Recharts, Chart.js, etc.)
- Implement color coding based on status fields
- Display health scores and alerts prominently

**Production Ready**: Yes for Phase 1 graphs ✅
**Phase 2 Ready**: Architecture in place, implementations pending 🔄
