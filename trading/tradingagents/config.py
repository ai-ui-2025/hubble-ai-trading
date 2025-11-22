"""
Configuration models for the trading system.

Provides structured, type-safe configuration for accounts, APIs, and LLMs.
Uses LangGraph's init_chat_model for unified multi-provider support.
"""

from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path
import os
import re
import yaml

# Global configuration storage
_CONFIG_CACHE: Optional[Dict] = None

# Mapping from provider name to config key
PROVIDER_CONFIG_KEYS: Dict[str, str] = {
    "openai": "openai_api_key",
    "deepseek": "deepseek_api_key", 
    "gemini": "gemini_api_key",
    "anthropic": "anthropic_api_key",
}


def _substitute_env_vars(value):
    """
    Recursively substitute environment variables in config values.
    
    Supports ${VAR_NAME} syntax. If the variable is not found, returns the original string.
    
    Args:
        value: Config value (can be dict, list, or string)
        
    Returns:
        Value with environment variables substituted
    """
    if isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    elif isinstance(value, str):
        # Replace ${VAR_NAME} with environment variable value
        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Return original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, value)
    else:
        return value


def load_yaml_config(config_file: str = None) -> Dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_file: Path to config file (default: from CONFIG_FILE env var or config.prod.yaml)
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config format is invalid
    """
    global _CONFIG_CACHE
    
    # Return cached config if available
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    
    # Determine config file: explicit arg > env var > default
    if config_file is None:
        config_file = os.getenv("CONFIG_FILE", "config.prod.yaml")
    
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file '{config_file}' not found. "
            f"Please create it or check the CONFIG_FILE environment variable."
        )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Config file format error: {e}")
    
    # Substitute environment variables in config values
    config = _substitute_env_vars(config)
    
    # Cache the config
    _CONFIG_CACHE = config
    return config


def detect_provider(model: str) -> str:
    """
    Detect LLM provider from model name.
    
    LangGraph's init_chat_model() automatically detects providers, but we need this
    for API key resolution. Returns lowercase provider name.
    """
    model_lower = model.lower()
    
    # OpenAI models
    if any(model_lower.startswith(prefix) for prefix in ["gpt-", "o1-", "o3-", "chatgpt-"]):
        return "openai"
    
    # DeepSeek models
    if "deepseek" in model_lower:
        return "deepseek"
    
    # Google Gemini models
    if "gemini" in model_lower:
        return "gemini"
    
    # Anthropic Claude models
    if "claude" in model_lower:
        return "anthropic"
    
    # Default to openai for unknown models
    return "openai"


def get_api_key_for_model(model: str, config: Optional[Dict] = None) -> str:
    """
    Get the appropriate API key for a model from configuration.
    
    Args:
        model: Model name (e.g., "gpt-4o-mini", "deepseek-chat", "gemini-pro")
        config: Optional configuration dict. If not provided, loads from config.yaml
        
    Returns:
        API key string
        
    Raises:
        ValueError: If the required API key is not found
    """
    if config is None:
        config = load_yaml_config()
    
    provider = detect_provider(model)
    config_key = PROVIDER_CONFIG_KEYS.get(provider)
    
    if not config_key:
        raise ValueError(f"Unknown provider '{provider}' for model '{model}'")
    
    llm_providers = config.get("llm_providers", {})
    api_key = llm_providers.get(config_key, "")
    
    if not api_key:
        raise ValueError(
            f"Missing '{config_key}' in config.yaml for model '{model}'. "
            f"Add it to the llm_providers section."
        )
    
    return api_key


@dataclass
class ExchangeConfig:
    """Exchange API configuration."""
    api_key: str
    api_secret: str
    base_url: str = "https://fapi.asterdex.com"
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.api_key:
            raise ValueError("api_key is required")
        if not self.api_secret:
            raise ValueError("api_secret is required")


@dataclass
class LLMConfig:
    """
    LLM configuration.
    
    Only the model name is needed - API keys come from config.yaml,
    temperature and max_tokens are hardcoded in the initialization.
    """
    model: str
    
    @property
    def provider(self) -> str:
        """Detect provider from model name."""
        return detect_provider(self.model)


@dataclass
class TestMode:
    """Test mode configuration for controlling trading decisions."""
    decision: Optional[str] = None  # Limit choices: "LONG", "LONG/SHORT", "LONG/SHORT/EXIT/HOLD" (None = all allowed)
    order_type: Optional[str] = None  # Force order type: MARKET, LIMIT (None = AI decides)
    
    def __post_init__(self):
        """Validate test mode parameters."""
        valid_decisions = ["LONG", "SHORT", "EXIT", "HOLD"]
        valid_order_types = ["MARKET", "LIMIT"]
        
        # Validate decision - can be single or multiple separated by /
        if self.decision:
            decisions = [d.strip() for d in self.decision.split("/")]
            for d in decisions:
                if d not in valid_decisions:
                    raise ValueError(f"Invalid decision '{d}', must be one of {valid_decisions}")
        
        if self.order_type and self.order_type not in valid_order_types:
            raise ValueError(f"order_type must be one of {valid_order_types}")


@dataclass
class AccountConfig:
    """Complete account configuration."""
    name: str
    symbol: str
    exchange: ExchangeConfig
    llm: LLMConfig
    trader_id: str
    enabled: bool = True
    description: str = ""
    test_mode: Optional[TestMode] = None  # Test mode: force specific decisions
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.name:
            raise ValueError("name is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if not self.trader_id:
            raise ValueError("trader_id is required")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "symbol": self.symbol,
            "llm_model": self.llm.model,
            "trader_id": self.trader_id,
            "description": self.description,
            "exchange": {
                "api_key": self.exchange.api_key,
                "api_secret": self.exchange.api_secret,
                "base_url": self.exchange.base_url,
            },
            "llm": {
                "model": self.llm.model,
            }
        }


def load_accounts_config(config_file: str = None) -> list[AccountConfig]:
    """
    Load account configurations from YAML file.
    
    Args:
        config_file: Path to configuration file (config.yaml)
        
    Returns:
        List of AccountConfig objects
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config format is invalid or missing API keys
    """
    # Load the YAML configuration
    config = load_yaml_config(config_file)
    
    accounts = []
    for account_dict in config.get("accounts", []):
        # Get LLM model name
        llm_model = account_dict.get("llm_model", "deepseek-chat")
        
        # Validate that the API key is available (will raise ValueError if not)
        try:
            get_api_key_for_model(llm_model, config)
        except ValueError as e:
            raise ValueError(f"Account '{account_dict.get('name', 'Unknown')}': {e}")
        
        # Get exchange config
        exchange_config = account_dict.get("exchange", {})
        
        # Get trader_id (required field)
        trader_id = account_dict.get("trader_id")
        if not trader_id:
            raise ValueError(f"Account '{account_dict.get('name', 'Unknown')}': trader_id is required")
        
        # Parse test_mode if provided
        test_mode = None
        test_mode_dict = account_dict.get("test_mode")
        if test_mode_dict:
            test_mode = TestMode(
                decision=test_mode_dict.get("decision"),
                order_type=test_mode_dict.get("order_type")
            )
        
        # Create structured config
        config_obj = AccountConfig(
            name=account_dict.get("name", "Unknown"),
            symbol=account_dict.get("symbol", "BTCUSDT"),
            enabled=account_dict.get("enabled", True),
            trader_id=trader_id,
            description=account_dict.get("description", ""),
            test_mode=test_mode,
            exchange=ExchangeConfig(
                api_key=exchange_config.get("api_key", ""),
                api_secret=exchange_config.get("api_secret", ""),
                base_url=exchange_config.get("base_url", "https://fapi.asterdex.com"),
            ),
            llm=LLMConfig(
                model=llm_model,
            )
        )
        
        accounts.append(config_obj)
    
    return accounts


def get_system_config(config_file: str = None) -> Dict:
    """
    Get system-level configuration.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        System configuration dictionary
    """
    config = load_yaml_config(config_file)
    return config.get("system", {
        "interval_minutes": 5,
        "log_dir": "./logs",
        "app_env": "prod",
        "require_trade": False
    })


def get_analysis_api_config(config_file: str = None) -> Dict:
    """
    Get analysis API configuration.

    Args:
        config_file: Path to configuration file

    Returns:
        Analysis API configuration dictionary with 'url' and 'auth' keys
    """
    config = load_yaml_config(config_file)
    return config.get("analysis_api", {
        "url": "",
        "auth": ""
    })


def get_research_agent_config(config_file: str = None) -> Dict:
    """
    Get research agent configuration (A2A Protocol).

    Args:
        config_file: Path to configuration file

    Returns:
        Research agent configuration dictionary with 'agent_id' and optional 'endpoint'
    """
    config = load_yaml_config(config_file)
    return config.get("research_agent", {
        "agent_id": "",  # Empty means auto-discover any available agent
        "endpoint": ""   # Optional: fallback endpoint if not found in ERC-8004
    })


def get_agent0_config(config_file: str = None) -> Dict:
    """
    Get agent0 SDK configuration.

    Args:
        config_file: Path to configuration file

    Returns:
        Agent0 configuration dictionary
    """
    config = load_yaml_config(config_file)
    return config.get("agent0", {
        "chain_id": 11155111,  # Default: Sepolia
        "rpc_url": None,
    })


def get_x402_config(config_file: str = None) -> Dict:
    """
    Get X402 payment protocol configuration.

    Args:
        config_file: Path to configuration file

    Returns:
        X402 configuration dictionary with 'wallet_private_key'
    """
    config = load_yaml_config(config_file)
    return config.get("x402", {
        "wallet_private_key": "",  # Can use ${WALLET_PRIVATE_KEY} in YAML
    })


def set_env_from_config(config_file: str = None) -> None:
    """
    Set environment variables from YAML config for backward compatibility.
    
    This allows existing code that reads from os.environ to continue working.
    
    Args:
        config_file: Path to configuration file
    """
    config = load_yaml_config(config_file)
    
    # Set system env
    system_config = config.get("system", {})
    if "app_env" in system_config:
        os.environ["APP_ENV"] = system_config["app_env"]
    
    # Set LLM API keys
    llm_providers = config.get("llm_providers", {})
    if llm_providers.get("openai_api_key"):
        os.environ["OPENAI_API_KEY"] = llm_providers["openai_api_key"]
    if llm_providers.get("deepseek_api_key"):
        os.environ["DEEPSEEK_API_KEY"] = llm_providers["deepseek_api_key"]
    if llm_providers.get("gemini_api_key"):
        os.environ["GEMINI_API_KEY"] = llm_providers["gemini_api_key"]
    if llm_providers.get("anthropic_api_key"):
        os.environ["ANTHROPIC_API_KEY"] = llm_providers["anthropic_api_key"]
    
    # Set analysis API config
    analysis_api = config.get("analysis_api", {})
    if analysis_api.get("url"):
        os.environ["ANALYSIS_API_URL"] = analysis_api["url"]
    if analysis_api.get("auth"):
        os.environ["ANALYSIS_API_AUTH"] = analysis_api["auth"]
    
    # Set X402 payment config
    x402_config = config.get("x402", {})
    if x402_config.get("wallet_private_key"):
        os.environ["WALLET_PRIVATE_KEY"] = x402_config["wallet_private_key"]
