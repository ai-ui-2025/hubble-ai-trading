# TradingAgents

![TradingAgents Workflow](assets/arch.svg)

Autonomous AI cryptocurrency trading system. Multi-agent collaboration for market analysis, risk management, and trade execution.

---

## 🤖 Agent Architecture

- **Technical Research Agent:** Market data analysis (candlesticks, indicators, funding rates, order book) via ERC8004 + A2A + X402
- **Risk Manager Agent:** Safety boundaries and risk assessment
- **Portfolio Manager Agent:** Capital allocation and position management
- **Trader Agent:** Trading decisions and execution planning
- **Summarizer Agent:** Performance reporting

---

## 🚀 Quick Start

**1. Install:**
```bash
uv sync
```

**2. Configure** (`config.prod.yaml` / `config.dev.yaml`):
```yaml
system:
  interval_minutes: 5

llm_providers:
  openai_api_key: "your-key"
  deepseek_api_key: "your-key"

accounts:
  - name: "Account1"
    enabled: true
    symbol: "BTCUSDT"
    llm_model: "deepseek-chat"
    exchange:
      api_key: "your-key"
      api_secret: "your-secret"
      base_url: "https://fapi.asterdex.com"
```

**3. Run:**
```bash
python main.py               # Production
python main.py --env dev     # Development
```

---

## 🧪 Test Mode

Control AI decisions for testing:

```yaml
accounts:
  - test_mode:
      decision: "LONG/SHORT"    # Limit choices: "EXIT", "LONG/SHORT", "HOLD", etc.
      order_type: "LIMIT"       # Force "MARKET" or "LIMIT"
```

**Examples:**
```yaml
# Test EXIT only
test_mode:
  decision: "EXIT"
  order_type: "MARKET"

# Test LONG with LIMIT orders
test_mode:
  decision: "LONG"
  order_type: "LIMIT"
```

---

## 📝 Logging

- `logs/orchestrator_*.log` - Main process
- `logs/accounts/AccountName_*.log` - Individual accounts
- `logs/error_*.log` - Errors

---

## 🛡️ Safety Features

**Protective Orders:**
- Atomic SL/TP updates (create before cancel)
- Trailing stop (never increases risk)
- Danger zone protection
- Auto-adjust quantities on position changes

**Position Management:**
- `close_position()` - Close + cancel all orders
- `reduce_position()` - Partial close + adjust SL/TP
- `update_sl_tp_safe()` - Safe updates with checks

**Risk Controls:**
- Margin monitoring
- Position sizing
- Leverage limits

---

## 🏗️ Architecture

- **LangGraph:** Multi-agent workflow with state-based communication
- **Tool-based:** Agents interact via tools (not direct calls)
- **Type-safe:** Pydantic models for all AI outputs
- **Closed-loop:** Analysis → Decision → Execution in agent graph

See `.cursorrules` for detailed guidelines.

---

## 📊 Structure

```
TradingAgents/
├── main.py                    # Entry point
├── config.{prod,dev}.yaml     # Configuration
├── tradingagents/
│   ├── agents/                # AI agents
│   ├── dataflows/             # Exchange APIs
│   ├── config.py              # Config management
│   └── trading_runner.py      # LangGraph workflow
└── logs/                      # Logs
```
