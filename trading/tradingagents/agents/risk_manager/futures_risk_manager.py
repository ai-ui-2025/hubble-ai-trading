"""
Futures risk manager agent.

Evaluates account status, position risk, and entry feasibility.
Outputs a clear, structured TEXT report for downstream agents.
"""

from loguru import logger

from tradingagents.agents.prompt_utils import build_collaboration_prompt
from tradingagents.agents.utils.analysis_recorder import record_agent_execution


def create_risk_manager(llm):
    """
    Build the futures risk manager node.
    
    Args:
        llm: Language model instance
        
    Returns:
        Risk manager node callable.
    """
    
    def risk_manager_node(state):
        symbol = state["trading_symbol"]

        # Import futures tools
        from tradingagents.agents.utils.futures_execution_tools import (
            get_comprehensive_trading_status,
        )
        from tradingagents.agents.utils.agent0_tools_a2a import (
            invoke_research_agent,
            discover_research_agents,
        )

        tools = [
            # Agent0 tools for research agent invocation
            invoke_research_agent,
            discover_research_agents,
            # Trading status tool
            get_comprehensive_trading_status,
        ]
        
        # Get reflection context if this is a reanalysis cycle
        reflection_context = ""
        reflection_count = state.get("reflection_count", 0)
        
        if reflection_count > 0:
            reflection_insights = state.get("reflection_insights", "")
            reflection_issues = state.get("reflection_issues", "")
            
            reflection_context = "\n\n🔄 **REFLECTION CONTEXT** (This is a reanalysis cycle)\n"
            if reflection_insights:
                reflection_context += f"📚 Previous Insights:\n{reflection_insights}\n\n"
            if reflection_issues:
                reflection_context += f"⚠️  Issues to Address:\n{reflection_issues}\n\n"
            reflection_context += "Please incorporate these learnings into your assessment.\n"
        
        # Get market timeframes from state
        market_timeframes = state.get("market_timeframes", {"primary": "1h", "secondary": ["5m", "15m"]})
        timeframes_json = str(market_timeframes).replace("'", '"')  # Convert to JSON-like string

        system_message = f"""You are a Risk Manager AI. Your audience is another AI agent (the Portfolio Manager).
{reflection_context}
**YOUR TASK:** Get market research, assess account/position status, then output a 'RISK ASSESSMENT' section.

**CRITICAL INSTRUCTIONS:**
1. **IGNORE** any previous reports in the conversation history. Your analysis must be based ONLY on fresh data from your tools.
2. **DO NOT** make trading decisions (LONG/SHORT/HOLD) - that's the Portfolio Manager's job.
3. **DO NOT** add any text before the `---` separator or after the final `---`.
4. Your entire output must be ONLY the markdown section below.
5. **IMPORTANT**: If the result shows `"position_exists": false`, this is NORMAL and you MUST still generate a complete report for the "NO position" case.

**EXECUTION WORKFLOW:**
1. **FIRST**: Call `invoke_research_agent(symbol="{symbol}", timeframes='{timeframes_json}')` to get market analysis from a research agent
   - This will automatically discover and invoke the best available research agent
   - Review the research_report and research_summary in the response

2. **SECOND**: Call `get_comprehensive_trading_status("{symbol}")` to get complete trading state (account + position + orders in one call)

3. **THIRD**: Generate your risk assessment based on BOTH the research report AND the account status
   - Consider market conditions from research report
   - Assess account health and position risk
   - ALWAYS generate a complete report even if there's no position

Use your tools to gather data, then fill in this EXACT template:

**YOUR OUTPUT (EXACTLY THIS FORMAT):**

---

## RISK ASSESSMENT

### Account Health
- Total-Equity: $X.XX
- Available-Balance: $X.XX
- Margin-Used: $X.XX
- Margin-Ratio: X.XX%
- Margin-Status: [HEALTHY/WARNING/CRITICAL]
- Account-Mode: [CROSS_MARGIN/ISOLATED]

### Current Position
[If NO position:]
- Position-Status: NONE
- Can-Enter-New: [YES/NO]
- Entry-Capacity: $X.XX USD (X.XX% of equity)
- Recommended-Leverage: Xx
- Reasoning: [One sentence on sizing rationale]

[If position EXISTS:]
- Position-Side: [LONG/SHORT]
- Position-Size: X.XX contracts
- Notional-Value: $X.XX USD
- Entry-Price: $X.XX
- Current-PnL: $X.XX (X.XX%)
- Position-Leverage: Xx
- Liquidation-Price: $X.XX
- Distance-to-Liquidation: X.XX%
- Risk-Level: [LOW/MEDIUM/HIGH/CRITICAL]

### Risk Flags
- [List specific concerns OR "None"]

### Capacity Assessment
- New-Position-Capacity: $X.XX USD
- Suggested-Position-Size: $X.XX USD (X.XX% of equity)
- Risk-Buffer: X.XX%
- Status: [READY/LIMITED/CONSTRAINED]

---

### 💭 Plain Language Summary

[Write 2-3 sentences in simple, natural language explaining your risk assessment. Focus on:
- Current account health (how much money is available, any active positions)
- Whether it's safe to enter new trades or if there are concerns
- Your recommendation for position sizing based on risk

Example: "The account has $10,000 total equity with $8,500 available for trading. There's currently no open position, so we're free to enter new trades. Based on the account size and volatility, I recommend keeping any new position under $2,000 to maintain safe risk levels."]

---

**STOP HERE. Do NOT write any other sections.**

Guidelines:
- Flag margin >60% as WARNING, >80% as CRITICAL
- Flag liquidation distance <10% as HIGH RISK, <5% as CRITICAL
- Suggest conservative sizing: 10-20% of equity typically
- Minimum position: $100 USD (below this, trading costs often exceed potential profits)
- NEVER return an empty report - always generate the full section even if there's no position
"""
        
        prompt = build_collaboration_prompt()
        
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        
        chain = prompt | llm.bind_tools(tools)
        # Extract and upload research agent result immediately (before LLM processing)
        # This ensures we capture the A2A interaction record as soon as it's available
        import json
        technical_research_report = ""
        research_error = None
        research_error_type = None
        
        # Check if we have a research agent response in the latest messages
        for msg in reversed(state["messages"][-5:]):  # Check last 5 messages
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    data = json.loads(msg.content)
                    
                    if "research_report" in data:
                        research_summary = data.get("research_summary", "")
                        research_json_value = data.get("jsonValue")
                        
                        # Upload immediately if we have the data
                        # CRITICAL: Check if we already recorded this to avoid duplicates
                        # The graph loop might cause this node to be visited multiple times
                        if research_json_value and research_summary:
                            if state.get("technical_research_report"):
                                logger.info("ℹ️ Research report already recorded in state, skipping duplicate upload.")
                            else:
                                logger.info(f"✅ Found research agent response (summary: {len(research_summary)} chars, jsonValue: {len(research_json_value)} chars)")
                                logger.info("📤 Uploading research agent execution record...")
                                record_agent_execution(
                                    state,
                                    "research_agent",
                                    research_summary,
                                    json_value=research_json_value
                                )
                        
                        # Store the report for use
                        if data.get("error"):
                            research_error = data["error"]
                            research_error_type = data.get("error_type", "UNKNOWN_ERROR")
                        elif data["research_report"]:
                            technical_research_report = data["research_report"]
                        
                        break
                        
                except (json.JSONDecodeError, TypeError):
                    continue
        
        result = chain.invoke(state["messages"])
        
        # Check if LLM wants to call tools
        # Only extract report when tool calling is complete
        risk_assessment = ""
        risk_assessment_summary = ""

        if not result.tool_calls or len(result.tool_calls) == 0:
            # Validate research report is available
            if not technical_research_report:
                # Build detailed error message based on error type
                if research_error_type == "X402_PAYMENT_FAILED":
                    error_details = (
                        "X402 payment failed. Please check:\n"
                        "  1. Wallet private key is correctly configured in config.yaml\n"
                        "  2. Wallet has sufficient balance for payment\n"
                        "  3. Network connectivity to payment provider"
                    )
                elif research_error_type == "CONNECTION_ERROR":
                    error_details = "Cannot connect to research agent. Check network and agent endpoint."
                elif research_error_type == "AGENT_NOT_FOUND":
                    error_details = "Research agent not found via ERC-8004 discovery. Check agent_id configuration."
                elif research_error_type == "SDK_NOT_INITIALIZED":
                    error_details = "Agent0 SDK not initialized. Check RPC configuration in config.yaml."
                else:
                    error_details = research_error or "Research agent did not return a report"
                
                error_msg = (
                    f"❌ CRITICAL: Cannot proceed without valid research report.\n"
                    f"Error Type: {research_error_type or 'UNKNOWN'}\n"
                    f"Details: {error_details}\n"
                    f"⚠️  Aborting trading cycle to prevent uninformed decisions."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            full_content = result.content

            # Split the report and summary
            # Look for "### 💭 Plain Language Summary" marker
            if "### 💭 Plain Language Summary" in full_content or "Plain Language Summary" in full_content:
                parts = full_content.split("### 💭 Plain Language Summary", 1)
                risk_assessment = parts[0].strip()

                # Extract summary (everything after the marker until the next "---" or end)
                if len(parts) > 1:
                    summary_section = parts[1].strip()
                    # Remove the ending "---" if present
                    summary_section = summary_section.split("---")[0].strip()
                    risk_assessment_summary = summary_section
            else:
                # Fallback: use full content as report if no summary section found
                risk_assessment = full_content

            logger.info(f"✅ Risk Assessment complete for {symbol}")
            logger.debug(f"Report length: {len(risk_assessment)} characters")
            logger.debug(f"Summary length: {len(risk_assessment_summary)} characters")

            # Record execution to external API
            # Only record human-friendly summary (not the full risk assessment)
            # record_agent_execution(state, "risk_manager", risk_assessment)  # Disabled: only upload summary
            if risk_assessment_summary:
                record_agent_execution(state, "risk_manager_summary", risk_assessment_summary)
        else:
            logger.debug(f"Risk Manager requesting {len(result.tool_calls)} tool calls")

        # Append to message history, don't replace it
        return {
            "messages": state["messages"] + [result],
            "risk_assessment": risk_assessment,
            "risk_assessment_summary": risk_assessment_summary,
            "technical_research_report": technical_research_report,
        }
    
    return risk_manager_node

