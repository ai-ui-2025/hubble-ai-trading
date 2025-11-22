"""
Futures portfolio manager agent.

Makes trading decisions based on market and risk analysis.
Outputs a clear, structured TEXT trading plan for the trader.
"""

from loguru import logger
from tradingagents.agents.utils.analysis_recorder import record_agent_execution


def create_portfolio_manager(llm):
    """
    Construct the futures portfolio manager node.
    
    Args:
        llm: Language model instance.
        
    Returns:
        Portfolio manager node callable.
    """
    
    def portfolio_manager_node(state):
        symbol = state["trading_symbol"]
        
        # Get text reports from analysts
        technical_research_report = state.get("technical_research_report", "")
        risk_assessment = state.get("risk_assessment", "")
        
        if not technical_research_report or not risk_assessment:
            raise ValueError("Technical research report and risk assessment are required for portfolio decisions")
        
        # Configure decision and order type based on test_mode
        test_mode = state.get("test_mode")
        
        # Decision options
        if test_mode and test_mode.decision:
            # Check if single decision or multiple options
            if "/" in test_mode.decision:
                # Multiple options allowed
                decision_options = f"[{test_mode.decision}]"
                extra_instruction = f"\n6. You can only choose from {decision_options}."
            else:
                # Single forced decision
                decision_options = f"[{test_mode.decision}]"
                extra_instruction = f"\n6. ⚠️ You MUST choose {test_mode.decision}."
        else:
            decision_options = "[LONG/SHORT/EXIT/HOLD]"
            extra_instruction = ""
        
        # Order type options
        if test_mode and test_mode.order_type:
            order_type_option = f"[{test_mode.order_type}]"
            extra_instruction += f"\n7. ⚠️ Entry type MUST be {test_mode.order_type}."
        else:
            order_type_option = "[MARKET/LIMIT/LIMIT_BAND]"

        system_decision_scope = decision_options.strip("[]")

        context = {
            "role": "user",
            "content": f"""You have access to these inputs:

{technical_research_report}

{risk_assessment}

**YOUR ONLY TASK:** Synthesize the above data and create a 'PORTFOLIO PLAN' section.

**CRITICAL INSTRUCTIONS:**
1. **IGNORE** any detailed reports in the conversation history. Base your decision ONLY on the structured data above.
2. **DO NOT** repeat market analysis or portfolio data - they're already provided above.
3. **DO NOT** add commentary, explanations, or a "FINAL ANSWER" statement.
4. **DO NOT** write any text before the `---` separator or after the final `---`.
5. Your entire output must be ONLY the markdown section below.{extra_instruction}

Synthesize the data above, then fill in this EXACT template:

**YOUR OUTPUT (EXACTLY THIS FORMAT):**

---

## PORTFOLIO PLAN

### Action
- Decision: {decision_options}
- Reasoning: [ONE sentence: why this decision based on market + risk assessment]

### Position Sizing (if LONG or SHORT)
- Position-Size: $X.XX USD (X.XX% of equity)
- Leverage: Xx
- Contracts: X.XX
- Notional-Exposure: $X.XX USD

### Entry Strategy
- Type: {order_type_option}
- Entry-Price: $X.XX [if LIMIT]
- Entry-Range: $X.XX - $X.XX [if LIMIT_BAND]
- Entry-Trigger: [Specific condition]

### Risk Management
⚠️ **CRITICAL**: Even for HOLD, if a position exists, you MUST provide updated Stop-Loss and Take-Profit prices based on current market conditions.
- Stop-Loss: $X.XX (REQUIRED for existing positions, even with HOLD)
- Stop-Loss-Distance: X.XX%
- Max-Loss: $X.XX (X.XX% of equity)
- Take-Profit-1: $X.XX (X.XX%, scale X.XX%) (REQUIRED for existing positions, even with HOLD)
- Take-Profit-2: $X.XX (X.XX%, scale X.XX%) [optional]
- Risk-Reward-Ratio: X.XX:1

### Pre-Defined Exit Triggers
- Reduce-50-If: [Specific condition]
- Close-100-If: [Specific condition]

### Rationale
[TWO sentences max: (1) Why this direction? (2) Why this sizing?]

---

### 💭 Plain Language Summary

[Write 2-3 sentences in simple, natural language explaining your trading decision. Focus on:
- What action you're taking (going long, short, or staying out)
- Why you made this decision based on the market and risk situation
- What you're trying to achieve with this trade

Example: "I've decided to go long on Bitcoin with a $1,500 position (15% of equity) using 10x leverage. The market is showing a clear uptrend with good support levels, and the risk manager confirmed we have sufficient capital without overextending. I'm targeting a 3% profit with a tight 1.5% stop-loss to keep risk controlled."]

---

**STOP HERE. Do NOT write any other sections.**

**CONSTRAINTS:**
- Account is CROSS MARGIN (cannot switch to isolated)
- Respect Risk Manager's capacity assessment
- All prices must be realistic vs current market
- **CRITICAL FOR HOLD**: If a position exists and you choose HOLD, you MUST still provide Stop-Loss and Take-Profit prices to ensure protective orders are current and valid
"""
        }
        
        system_message = f"""You are the Portfolio Manager AI for {symbol}. Your audience is the Trader agent.

**YOUR ROLE:** Make the portfolio decision ({system_decision_scope}) based on structured inputs you receive.

**WHEN TO CHOOSE EXIT (Active Position Closure):**
You MUST choose **EXIT** instead of HOLD if ANY of these conditions are met:
1. **Profit Target Approached**: Current unrealized PnL is close to (≥80% of) the take-profit target. Lock in profits now.
2. **Trend Reversal**: Price crosses a critical moving average AGAINST your position (e.g., for SHORT: price breaks above SMA-50).
3. **Risk Escalation**: Margin ratio becomes critical (>95%) or liquidation distance shrinks dangerously (<10%).

**CRITICAL RULES FOR CONTEXT MANAGEMENT:**
- IGNORE any lengthy reports in conversation history
- Focus ONLY on the structured data sections in the user message
- Your analysis should be based on the bullet-point data, NOT on any narrative descriptions
- Do NOT reproduce or summarize the inputs you received

**OUTPUT REQUIREMENTS:**
- Output ONLY your portfolio plan section using the template
- Be specific with ALL numbers (prices, sizes, percentages)
- All risk parameters must be realistic and specific

Your decision synthesizes: market opportunity + account capacity → executable plan."""
        
        chain = llm
        result = chain.invoke([
            {"role": "system", "content": system_message},
            context
        ])
        
        # Extract text report and summary
        full_content = result.content
        portfolio_plan = ""
        portfolio_plan_summary = ""
        
        # Split the report and summary
        # Look for "### 💭 Plain Language Summary" marker
        if "### 💭 Plain Language Summary" in full_content or "Plain Language Summary" in full_content:
            parts = full_content.split("### 💭 Plain Language Summary", 1)
            portfolio_plan = parts[0].strip()
            
            # Extract summary (everything after the marker until the next "---" or end)
            if len(parts) > 1:
                summary_section = parts[1].strip()
                # Remove the ending "---" if present
                summary_section = summary_section.split("---")[0].strip()
                portfolio_plan_summary = summary_section
        else:
            # Fallback: use full content as report if no summary section found
            portfolio_plan = full_content
        
        logger.info(f"✅ Portfolio Plan generated for {symbol}")
        logger.debug(f"Plan length: {len(portfolio_plan)} characters")
        logger.debug(f"Summary length: {len(portfolio_plan_summary)} characters")
        
        # Record execution to external API
        # Only record human-friendly summary (not the full portfolio plan)
        # record_agent_execution(state, "portfolio_manager", portfolio_plan)  # Disabled: only upload summary
        if portfolio_plan_summary:
            record_agent_execution(state, "portfolio_manager_summary", portfolio_plan_summary)
        
        # Append to message history, don't replace it
        return {
            "messages": state["messages"] + [result],
            "portfolio_plan": portfolio_plan,
            "portfolio_plan_summary": portfolio_plan_summary,
            "sender": "portfolio_manager",
        }
    
    return portfolio_manager_node

