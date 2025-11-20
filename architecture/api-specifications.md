# API Specifications - Quantum Financial System

## API Design Principles

1. **RESTful Design**: Standard HTTP methods and status codes
2. **Versioning**: URL-based versioning (e.g., `/api/v1/`, `/api/v2/`)
3. **Consistency**: Uniform response structure across all endpoints
4. **Security**: OAuth 2.0 + JWT authentication
5. **Rate Limiting**: Tiered rate limits based on user type
6. **Pagination**: Cursor-based pagination for large datasets
7. **HATEOAS**: Hypermedia links for resource navigation

## Standard Response Format

### Success Response
```json
{
  "status": "success",
  "data": {
    // Response payload
  },
  "metadata": {
    "timestamp": "2025-11-20T12:00:00Z",
    "request_id": "req_abc123xyz",
    "version": "v1"
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_ORDER",
    "message": "Order quantity exceeds position limit",
    "details": {
      "max_quantity": 1000,
      "requested_quantity": 1500
    }
  },
  "metadata": {
    "timestamp": "2025-11-20T12:00:00Z",
    "request_id": "req_abc123xyz"
  }
}
```

## Authentication

### OAuth 2.0 Flow

**1. Obtain Access Token**:
```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "grant_type": "password",
  "username": "user@example.com",
  "password": "secure_password",
  "client_id": "client_id",
  "client_secret": "client_secret"
}

Response:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**2. Use Access Token**:
```http
GET /api/v1/orders
Authorization: Bearer eyJhbGc...
```

**3. Refresh Token**:
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGc..."
}
```

## Trading APIs

### Order Management

#### Create Order
```http
POST /api/v1/orders
Authorization: Bearer {token}
Content-Type: application/json

{
  "symbol": "AAPL",
  "side": "buy",
  "type": "limit",
  "quantity": 100,
  "price": 150.50,
  "time_in_force": "GTC",
  "client_order_id": "order_123"
}

Response 201:
{
  "status": "success",
  "data": {
    "order_id": "ord_abc123",
    "client_order_id": "order_123",
    "symbol": "AAPL",
    "side": "buy",
    "type": "limit",
    "quantity": 100,
    "price": 150.50,
    "status": "pending",
    "filled_quantity": 0,
    "average_price": 0,
    "time_in_force": "GTC",
    "created_at": "2025-11-20T12:00:00Z",
    "updated_at": "2025-11-20T12:00:00Z"
  }
}
```

**Order Types**:
- `market`: Execute at best available price
- `limit`: Execute at specified price or better
- `stop`: Trigger market order when stop price reached
- `stop_limit`: Trigger limit order when stop price reached
- `trailing_stop`: Dynamic stop based on price movement
- `iceberg`: Large order split into smaller chunks
- `twap`: Time-weighted average price
- `vwap`: Volume-weighted average price

**Time in Force**:
- `GTC`: Good till cancelled
- `IOC`: Immediate or cancel
- `FOK`: Fill or kill
- `GTD`: Good till date
- `DAY`: Day order

#### Get Order
```http
GET /api/v1/orders/{order_id}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "order_id": "ord_abc123",
    "symbol": "AAPL",
    "side": "buy",
    "type": "limit",
    "quantity": 100,
    "price": 150.50,
    "status": "filled",
    "filled_quantity": 100,
    "average_price": 150.45,
    "fills": [
      {
        "fill_id": "fill_001",
        "quantity": 50,
        "price": 150.40,
        "timestamp": "2025-11-20T12:01:00Z"
      },
      {
        "fill_id": "fill_002",
        "quantity": 50,
        "price": 150.50,
        "timestamp": "2025-11-20T12:01:30Z"
      }
    ],
    "created_at": "2025-11-20T12:00:00Z",
    "updated_at": "2025-11-20T12:01:30Z"
  }
}
```

#### List Orders
```http
GET /api/v1/orders?status=open&symbol=AAPL&limit=50&cursor=abc123
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "orders": [
      // Array of order objects
    ],
    "pagination": {
      "next_cursor": "xyz789",
      "has_more": true,
      "total_count": 150
    }
  }
}
```

#### Cancel Order
```http
DELETE /api/v1/orders/{order_id}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "order_id": "ord_abc123",
    "status": "cancelled",
    "cancelled_at": "2025-11-20T12:05:00Z"
  }
}
```

#### Batch Order Operations
```http
POST /api/v1/orders/batch
Authorization: Bearer {token}
Content-Type: application/json

{
  "orders": [
    {
      "symbol": "AAPL",
      "side": "buy",
      "type": "limit",
      "quantity": 100,
      "price": 150.50
    },
    {
      "symbol": "GOOGL",
      "side": "sell",
      "type": "market",
      "quantity": 50
    }
  ]
}

Response 200:
{
  "status": "success",
  "data": {
    "results": [
      {
        "index": 0,
        "success": true,
        "order_id": "ord_abc123"
      },
      {
        "index": 1,
        "success": false,
        "error": "Insufficient balance"
      }
    ]
  }
}
```

### Market Data APIs

#### Get Real-time Quote
```http
GET /api/v1/market/quote/{symbol}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "symbol": "AAPL",
    "bid": 150.45,
    "ask": 150.50,
    "bid_size": 500,
    "ask_size": 300,
    "last_price": 150.48,
    "volume": 5000000,
    "timestamp": "2025-11-20T12:00:00.123Z"
  }
}
```

#### Get Order Book
```http
GET /api/v1/market/orderbook/{symbol}?depth=10
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "symbol": "AAPL",
    "bids": [
      [150.45, 500],  // [price, quantity]
      [150.44, 300],
      [150.43, 200]
    ],
    "asks": [
      [150.50, 300],
      [150.51, 400],
      [150.52, 250]
    ],
    "timestamp": "2025-11-20T12:00:00.123Z"
  }
}
```

#### Get Historical Data
```http
GET /api/v1/market/history/{symbol}?interval=1m&start=2025-11-20T00:00:00Z&end=2025-11-20T12:00:00Z
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "symbol": "AAPL",
    "interval": "1m",
    "bars": [
      {
        "timestamp": "2025-11-20T00:00:00Z",
        "open": 150.00,
        "high": 150.20,
        "low": 149.90,
        "close": 150.10,
        "volume": 10000
      }
      // More bars...
    ]
  }
}
```

#### Get Trade History
```http
GET /api/v1/market/trades/{symbol}?limit=100
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "symbol": "AAPL",
    "trades": [
      {
        "trade_id": "trade_001",
        "price": 150.50,
        "quantity": 100,
        "side": "buy",
        "timestamp": "2025-11-20T12:00:00.123Z"
      }
      // More trades...
    ]
  }
}
```

## Risk Management APIs

### Portfolio APIs

#### Get Portfolio
```http
GET /api/v1/portfolio
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "account_id": "acc_123",
    "total_value": 1000000.00,
    "cash_balance": 500000.00,
    "positions": [
      {
        "symbol": "AAPL",
        "quantity": 1000,
        "average_cost": 145.00,
        "current_price": 150.50,
        "market_value": 150500.00,
        "unrealized_pnl": 5500.00,
        "unrealized_pnl_percent": 3.79
      }
    ],
    "daily_pnl": 2500.00,
    "total_pnl": 10000.00
  }
}
```

#### Get Risk Metrics
```http
GET /api/v1/risk/metrics
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "var_95": 25000.00,
    "var_99": 40000.00,
    "expected_shortfall": 45000.00,
    "sharpe_ratio": 1.85,
    "max_drawdown": -0.12,
    "beta": 1.05,
    "volatility": 0.18,
    "leverage": 1.5,
    "margin_usage": 0.65
  }
}
```

### Quantum Risk APIs

#### Calculate Quantum VaR
```http
POST /api/v1/risk/quantum/var
Authorization: Bearer {token}
Content-Type: application/json

{
  "portfolio_id": "port_123",
  "confidence_level": 0.95,
  "time_horizon_days": 1,
  "backend": "ibm_quantum"
}

Response 202:
{
  "status": "accepted",
  "data": {
    "job_id": "qjob_abc123",
    "status": "queued",
    "estimated_completion": "2025-11-20T12:05:00Z"
  }
}
```

#### Get Quantum Job Status
```http
GET /api/v1/risk/quantum/jobs/{job_id}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "job_id": "qjob_abc123",
    "status": "completed",
    "result": {
      "var_95": 24850.00,
      "confidence_interval": [24500.00, 25200.00],
      "execution_time_seconds": 3.2,
      "qubits_used": 20,
      "quantum_backend": "ibm_quantum"
    },
    "submitted_at": "2025-11-20T12:00:00Z",
    "completed_at": "2025-11-20T12:00:03Z"
  }
}
```

#### Quantum Portfolio Optimization
```http
POST /api/v1/risk/quantum/optimize
Authorization: Bearer {token}
Content-Type: application/json

{
  "assets": ["AAPL", "GOOGL", "MSFT", "AMZN"],
  "constraints": {
    "min_weight": 0.05,
    "max_weight": 0.40,
    "max_volatility": 0.15,
    "target_return": 0.12
  },
  "objective": "maximize_sharpe"
}

Response 202:
{
  "status": "accepted",
  "data": {
    "job_id": "qjob_opt_123",
    "status": "queued"
  }
}

// Later, when checking job status:
GET /api/v1/risk/quantum/jobs/qjob_opt_123

Response 200:
{
  "status": "success",
  "data": {
    "job_id": "qjob_opt_123",
    "status": "completed",
    "result": {
      "optimal_weights": {
        "AAPL": 0.25,
        "GOOGL": 0.30,
        "MSFT": 0.35,
        "AMZN": 0.10
      },
      "expected_return": 0.125,
      "volatility": 0.142,
      "sharpe_ratio": 2.15
    }
  }
}
```

### URT+ Universal Optimization APIs

#### URT+ Multi-Market Optimization

```http
POST /api/v1/urt/optimize
Authorization: Bearer {token}
Content-Type: application/json

{
  "portfolio_id": "port_123",
  "markets": {
    "crypto": {
      "assets": ["BTC", "ETH", "SOL"],
      "expected_returns": [0.15, 0.12, 0.18],
      "max_exposure": 0.30
    },
    "stocks": {
      "assets": ["AAPL", "GOOGL", "MSFT"],
      "expected_returns": [0.08, 0.10, 0.09],
      "max_exposure": 0.40
    },
    "forex": {
      "assets": ["EUR/USD", "GBP/USD"],
      "expected_returns": [0.02, 0.03],
      "max_exposure": 0.20
    },
    "commodities": {
      "assets": ["GOLD", "OIL"],
      "expected_returns": [0.05, 0.07],
      "max_exposure": 0.20
    },
    "derivatives": {
      "assets": ["SPX_OPT"],
      "expected_returns": [0.12],
      "max_exposure": 0.15
    }
  },
  "constraints": {
    "position_limits": {
      "BTC": 0.15,
      "ETH": 0.15,
      "SOL": 0.10
    },
    "max_transaction_cost": 0.01,
    "max_correlation_exposure": 0.70,
    "drift_thresholds": {
      "default": 0.05,
      "crypto": 0.10
    }
  },
  "optimization_parameters": {
    "risk_aversion": 0.5,
    "cost_sensitivity": 0.3,
    "impact_sensitivity": 0.2,
    "quantum_backend": "ibm_quantum",
    "qaoa_layers": 5
  }
}

Response 202:
{
  "status": "accepted",
  "data": {
    "optimization_id": "urt_opt_abc123",
    "status": "queued",
    "estimated_completion": "2025-11-20T12:00:10Z",
    "quantum_job_id": "qjob_urt_001"
  },
  "metadata": {
    "timestamp": "2025-11-20T12:00:00Z",
    "request_id": "req_xyz789"
  }
}
```

#### Get URT+ Optimization Result

```http
GET /api/v1/urt/optimize/{optimization_id}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "optimization_id": "urt_opt_abc123",
    "status": "completed",
    "optimal_allocation": {
      "crypto": {
        "BTC": 0.12,
        "ETH": 0.10,
        "SOL": 0.08
      },
      "stocks": {
        "AAPL": 0.15,
        "GOOGL": 0.15,
        "MSFT": 0.10
      },
      "forex": {
        "EUR/USD": 0.08,
        "GBP/USD": 0.07
      },
      "commodities": {
        "GOLD": 0.08,
        "OIL": 0.04
      },
      "derivatives": {
        "SPX_OPT": 0.03
      }
    },
    "performance_metrics": {
      "expected_return": 0.0925,
      "portfolio_risk": 0.1245,
      "sharpe_ratio": 2.43,
      "portfolio_variance": 0.0155,
      "transaction_costs": 0.0082,
      "market_impact": 0.0015,
      "objective_value": 0.0847
    },
    "market_breakdown": {
      "crypto": 0.30,
      "stocks": 0.40,
      "forex": 0.15,
      "commodities": 0.12,
      "derivatives": 0.03
    },
    "constraint_satisfaction": {
      "total_allocation": 1.0000,
      "position_limits": "satisfied",
      "market_exposure_limits": "satisfied",
      "transaction_cost_limit": "satisfied",
      "correlation_limit": "satisfied"
    },
    "quantum_execution_info": {
      "backend_used": "ibm_quantum_jakarta",
      "qubits_used": 45,
      "circuit_depth": 128,
      "execution_time_seconds": 8.7,
      "qaoa_layers": 5,
      "optimization_iterations": 247
    }
  },
  "metadata": {
    "timestamp": "2025-11-20T12:00:10Z",
    "computation_time_ms": 8732
  }
}
```

#### URT+ Real-Time Rebalancing Monitor

```http
GET /api/v1/urt/rebalance/monitor/{portfolio_id}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "portfolio_id": "port_123",
    "current_allocation": {
      "crypto": 0.35,
      "stocks": 0.38,
      "forex": 0.14,
      "commodities": 0.10,
      "derivatives": 0.03
    },
    "target_allocation": {
      "crypto": 0.30,
      "stocks": 0.40,
      "forex": 0.15,
      "commodities": 0.12,
      "derivatives": 0.03
    },
    "drift_analysis": {
      "crypto": {
        "current_weight": 0.35,
        "target_weight": 0.30,
        "drift": 0.05,
        "drift_percentage": 16.67,
        "threshold": 0.10,
        "status": "within_threshold"
      },
      "stocks": {
        "current_weight": 0.38,
        "target_weight": 0.40,
        "drift": -0.02,
        "drift_percentage": -5.00,
        "threshold": 0.05,
        "status": "within_threshold"
      },
      "forex": {
        "current_weight": 0.14,
        "target_weight": 0.15,
        "drift": -0.01,
        "drift_percentage": -6.67,
        "threshold": 0.05,
        "status": "exceeded_threshold"
      }
    },
    "rebalance_recommendation": {
      "action": "rebalance",
      "reason": "forex_drift_exceeded",
      "priority": "medium",
      "estimated_cost": 0.0045,
      "estimated_impact": 0.0012
    }
  }
}
```

#### Trigger URT+ Rebalancing

```http
POST /api/v1/urt/rebalance
Authorization: Bearer {token}
Content-Type: application/json

{
  "portfolio_id": "port_123",
  "rebalance_type": "full",
  "execution_strategy": {
    "type": "twap",
    "duration_minutes": 30,
    "allow_partial": true
  },
  "constraints": {
    "max_transaction_cost": 0.01,
    "max_slippage": 0.005,
    "respect_market_hours": true
  }
}

Response 202:
{
  "status": "accepted",
  "data": {
    "rebalance_id": "rebal_xyz789",
    "status": "executing",
    "orders_created": 15,
    "estimated_completion": "2025-11-20T12:30:00Z"
  }
}
```

#### URT+ Cross-Market Correlation Analysis

```http
POST /api/v1/urt/correlation/analyze
Authorization: Bearer {token}
Content-Type: application/json

{
  "markets": ["crypto", "stocks", "forex", "commodities"],
  "time_period": "30d",
  "granularity": "1h"
}

Response 200:
{
  "status": "success",
  "data": {
    "correlation_matrix": {
      "crypto_stocks": 0.45,
      "crypto_forex": 0.12,
      "crypto_commodities": 0.28,
      "stocks_forex": 0.34,
      "stocks_commodities": 0.52,
      "forex_commodities": 0.19
    },
    "risk_exposure": {
      "total_correlated_exposure": 0.58,
      "max_correlation": 0.52,
      "threshold": 0.70,
      "status": "within_limit"
    },
    "diversification_score": 0.78,
    "recommendations": [
      "Current multi-market allocation provides good diversification",
      "Crypto and forex show low correlation - good hedge",
      "Consider reducing stocks-commodities exposure if correlation increases"
    ]
  }
}
```

#### URT+ Transaction Cost Routing Optimization

```http
POST /api/v1/urt/routing/optimize
Authorization: Bearer {token}
Content-Type: application/json

{
  "trades": [
    {
      "market": "crypto",
      "asset": "BTC",
      "quantity": 1.5,
      "platforms": ["binance", "coinbase", "kraken"]
    },
    {
      "market": "stocks",
      "asset": "AAPL",
      "quantity": 1000,
      "platforms": ["nyse", "nasdaq", "arca"]
    }
  ],
  "optimization_objective": "minimize_total_cost",
  "constraints": {
    "max_platform_allocation": 0.50,
    "preferred_platforms": ["binance", "nyse"]
  }
}

Response 200:
{
  "status": "success",
  "data": {
    "optimal_routing": [
      {
        "trade_id": "trade_001",
        "asset": "BTC",
        "quantity": 1.5,
        "routing_plan": {
          "binance": {
            "quantity": 0.9,
            "cost": 0.0009,
            "estimated_slippage": 0.0003
          },
          "kraken": {
            "quantity": 0.6,
            "cost": 0.0012,
            "estimated_slippage": 0.0004
          }
        },
        "total_cost": 0.0021,
        "total_slippage": 0.0007,
        "savings_vs_single_platform": 0.0015
      },
      {
        "trade_id": "trade_002",
        "asset": "AAPL",
        "quantity": 1000,
        "routing_plan": {
          "nyse": {
            "quantity": 700,
            "cost": 0.00035,
            "estimated_slippage": 0.00015
          },
          "arca": {
            "quantity": 300,
            "cost": 0.00015,
            "estimated_slippage": 0.00010
          }
        },
        "total_cost": 0.00050,
        "total_slippage": 0.00025,
        "savings_vs_single_platform": 0.00020
      }
    ],
    "aggregate_metrics": {
      "total_transaction_cost": 0.00260,
      "total_slippage": 0.00095,
      "total_savings": 0.00170,
      "optimization_improvement": "39.5%"
    }
  }
}
```

#### URT+ Historical Performance

```http
GET /api/v1/urt/performance/history?portfolio_id=port_123&period=90d
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "portfolio_id": "port_123",
    "period": "90d",
    "performance_summary": {
      "total_return": 0.1245,
      "annualized_return": 0.5235,
      "volatility": 0.1523,
      "sharpe_ratio": 3.44,
      "max_drawdown": -0.0823,
      "win_rate": 0.68
    },
    "market_contribution": {
      "crypto": 0.0456,
      "stocks": 0.0512,
      "forex": 0.0089,
      "commodities": 0.0134,
      "derivatives": 0.0054
    },
    "rebalancing_history": {
      "total_rebalances": 12,
      "triggered_by_drift": 8,
      "triggered_by_market_conditions": 4,
      "average_rebalance_cost": 0.0065,
      "average_improvement": 0.0234
    },
    "cost_analysis": {
      "total_transaction_costs": 0.0782,
      "total_market_impact": 0.0245,
      "routing_optimization_savings": 0.0312
    }
  }
}
```

## Settlement & Payment APIs

### Settlement APIs

#### Get Settlement Status
```http
GET /api/v1/settlement/{trade_id}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "trade_id": "trade_123",
    "settlement_status": "settled",
    "settlement_date": "2025-11-20",
    "cash_movement": {
      "currency": "USD",
      "amount": -15050.00,
      "direction": "debit"
    },
    "asset_movement": {
      "symbol": "AAPL",
      "quantity": 100,
      "direction": "credit"
    },
    "blockchain_tx_hash": "0x123abc...",
    "settled_at": "2025-11-20T16:00:00Z"
  }
}
```

### Payment APIs

#### Initiate Payment
```http
POST /api/v1/payments
Authorization: Bearer {token}
Content-Type: application/json

{
  "amount": 10000.00,
  "currency": "USD",
  "payment_method": "bank_transfer",
  "destination": {
    "account_number": "123456789",
    "routing_number": "021000021",
    "bank_name": "Bank of America"
  }
}

Response 202:
{
  "status": "accepted",
  "data": {
    "payment_id": "pay_123",
    "status": "pending",
    "estimated_completion": "2025-11-20T18:00:00Z"
  }
}
```

#### Get Payment Status
```http
GET /api/v1/payments/{payment_id}
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "payment_id": "pay_123",
    "status": "completed",
    "amount": 10000.00,
    "currency": "USD",
    "fees": 10.00,
    "net_amount": 9990.00,
    "completed_at": "2025-11-20T17:30:00Z"
  }
}
```

## Analytics APIs

#### Get Trading Analytics
```http
GET /api/v1/analytics/trading?period=7d
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "data": {
    "period": "7d",
    "total_trades": 150,
    "winning_trades": 95,
    "losing_trades": 55,
    "win_rate": 0.633,
    "total_pnl": 15000.00,
    "average_pnl_per_trade": 100.00,
    "largest_win": 2500.00,
    "largest_loss": -1200.00,
    "sharpe_ratio": 1.85,
    "max_drawdown": -0.08
  }
}
```

## WebSocket APIs

### Market Data Stream

```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://api.qfs.com/ws/market');

// Authenticate
ws.send(JSON.stringify({
  type: 'auth',
  token: 'eyJhbGc...'
}));

// Subscribe to market data
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['level2', 'trades'],
  symbols: ['AAPL', 'GOOGL']
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
  /*
  {
    "type": "level2_update",
    "symbol": "AAPL",
    "bids": [[150.45, 500]],
    "asks": [[150.50, 300]],
    "timestamp": "2025-11-20T12:00:00.123Z"
  }
  */
};
```

### Order Updates Stream

```javascript
// Subscribe to order updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['orders']
}));

// Receive order updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  /*
  {
    "type": "order_update",
    "order_id": "ord_abc123",
    "status": "filled",
    "filled_quantity": 100,
    "average_price": 150.45,
    "timestamp": "2025-11-20T12:00:00.123Z"
  }
  */
};
```

## Rate Limiting

### Rate Limit Tiers

| Tier | Requests/Second | Requests/Hour | WebSocket Connections |
|------|----------------|---------------|----------------------|
| Free | 10 | 1,000 | 1 |
| Basic | 100 | 10,000 | 5 |
| Pro | 1,000 | 100,000 | 20 |
| Enterprise | Custom | Custom | Custom |

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1732104000
```

### Rate Limit Exceeded Response

```http
HTTP/1.1 429 Too Many Requests

{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Retry after 60 seconds",
    "retry_after": 60
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| INVALID_REQUEST | 400 | Malformed request |
| UNAUTHORIZED | 401 | Invalid or missing authentication |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| INVALID_ORDER | 400 | Order validation failed |
| INSUFFICIENT_BALANCE | 400 | Not enough funds |
| MARKET_CLOSED | 400 | Market is closed |
| POSITION_LIMIT_EXCEEDED | 400 | Position limit exceeded |
| QUANTUM_JOB_FAILED | 500 | Quantum computation failed |

## API Versioning

**Current Version**: v1
**Deprecated Versions**: None
**Sunset Policy**: 12 months notice before deprecation

**Version Header**:
```http
API-Version: v1
```

## SDK Support

Official SDKs available for:
- Python
- JavaScript/TypeScript
- Java
- Go
- Rust
- C#

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-20
