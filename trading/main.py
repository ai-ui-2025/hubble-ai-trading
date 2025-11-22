#!/usr/bin/env python3
"""
AI Futures Trading System - Main Entry Point

Runs all enabled accounts continuously at configured intervals.

Usage:
    python main.py              # Load config.prod.yaml (default)
    python main.py --env dev    # Load config.dev.yaml
    python main.py --env prod   # Load config.prod.yaml
    
Configuration:
    - Production: config.prod.yaml
    - Development: config.dev.yaml
"""

import argparse
import multiprocessing
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logger (only for orchestrator, not for child processes)
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)

INTERVAL_MINUTES = 5

# Global timestamp for this run (shared across all processes)
_RUN_TIMESTAMP = None

def init_orchestrator_logger():
    """Initialize logger for the main orchestrator process only."""
    global _RUN_TIMESTAMP
    _RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.remove()
    # Console output (INFO and above)
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    # General log file (DEBUG and above)
    logger.add(
        log_dir / f"orchestrator_{_RUN_TIMESTAMP}.log",
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG"
    )
    # Separate error log file (WARNING and above)
    logger.add(
        log_dir / f"error_{_RUN_TIMESTAMP}.log",
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="WARNING",
        backtrace=True,
        diagnose=True
    )

def load_config(config_file="config.yaml"):
    """
    Load account configuration file.
    
    Args:
        config_file: Path to config.yaml
        
    Returns:
        List of AccountConfig objects
    """
    try:
        from tradingagents.config import (
            load_accounts_config, 
            get_system_config,
            set_env_from_config
        )
        
        # Set environment variables from config for backward compatibility
        set_env_from_config(config_file)
        
        # Load system config and update globals
        global INTERVAL_MINUTES
        system_config = get_system_config(config_file)
        INTERVAL_MINUTES = system_config.get("interval_minutes", 5)
        
        return load_accounts_config(config_file)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Config validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)


def run_account_process(account_config, run_timestamp):
    """
    Run trading strategy for a single account in a separate process.
    
    Each account gets its own dedicated log file for better isolation and traceability.
    
    Args:
        account_config: AccountConfig object with explicit configuration
        run_timestamp: Shared timestamp for this run (to keep log files organized)
    """
    account_name = account_config.name
    
    # Configure account-specific logger
    from loguru import logger as account_logger
    
    # Create account logs directory
    account_log_dir = Path("./logs/accounts")
    account_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Remove default handlers and configure account-specific logging
    account_logger.remove()
    
    # Console output with account prefix
    account_logger.add(
        sys.stdout,
        colorize=True,
        format=f"<cyan>[{account_name}]</cyan> <green>{{time:HH:mm:ss}}</green> | <level>{{level: <8}}</level> | <level>{{message}}</level>",
        level="INFO"
    )
    
    # Account-specific log file (all levels)
    account_logger.add(
        account_log_dir / f"{account_name}_{run_timestamp}.log",
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG"
    )
    
    # Account-specific error log
    account_logger.add(
        account_log_dir / f"{account_name}_error_{run_timestamp}.log",
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="WARNING",
        backtrace=True,
        diagnose=True
    )
    
    try:
        # Import trading function
        from tradingagents.trading_runner import run_trading_strategy
        
        account_logger.info(f"Starting trading for {account_config.symbol}")
        account_logger.info(f"Using LLM: {account_config.llm.model}")
        account_logger.info(f"Exchange: {account_config.exchange.base_url}")
        
        # Pass explicit configuration to trading strategy
        result = run_trading_strategy(
            symbol=account_config.symbol,
            config=account_config
        )
        
        if result:
            account_logger.success(f"Completed successfully")
            logger.success(f"[{account_name}] Completed successfully")
            return True
        else:
            account_logger.error(f"Failed")
            logger.error(f"[{account_name}] Failed")
            return False
            
    except Exception as e:
        account_logger.exception(f"Error: {e}")
        logger.error(f"[{account_name}] Error: {e}")
        return False


def run_all_accounts(accounts_config):
    """
    Run all enabled accounts in parallel using multiprocessing.
    
    Args:
        accounts_config: List of AccountConfig objects
    
    Returns:
        bool: True if all accounts succeeded
    """
    enabled_accounts = [acc for acc in accounts_config if acc.enabled]
    
    if not enabled_accounts:
        logger.error("No enabled accounts found")
        return False
    
    logger.info("="*80)
    logger.info("🚀 Multi-Account Trading System")
    logger.info("="*80)
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Enabled accounts: {len(enabled_accounts)}")
    
    for acc in enabled_accounts:
        logger.info(f"  📊 {acc.name}")
        logger.info(f"     Symbol: {acc.symbol}")
        logger.info(f"     Model: {acc.llm.model}")
        if acc.description:
            logger.info(f"     Description: {acc.description}")
    
    logger.info("="*80)
    logger.info("⏳ Starting parallel execution...")
    logger.info("="*80)
    
    # Get shared timestamp for all processes
    global _RUN_TIMESTAMP
    
    # Create and start processes
    processes = []
    for account_config in enabled_accounts:
        process = multiprocessing.Process(
            target=run_account_process,
            args=(account_config, _RUN_TIMESTAMP),
            name=account_config.name
        )
        processes.append((account_config.name, process))
        process.start()
        
        # Stagger the starts to avoid API rate limits
        time.sleep(2)
    
    # Wait for all processes to complete
    logger.info(f"⏳ Waiting for {len(processes)} accounts to complete...")
    
    results = []
    for name, process in processes:
        process.join()
        success = process.exitcode == 0
        results.append((name, success))
        
        if success:
            logger.success(f"{name} finished")
        else:
            logger.error(f"{name} failed (exit code: {process.exitcode})")
    
    # Print summary
    logger.info("="*80)
    logger.info("📊 Execution Summary")
    logger.info("="*80)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    logger.info(f"Total accounts: {total_count}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {total_count - success_count}")
    
    for name, success in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {name}")
    
    logger.info("="*80)
    
    return success_count == total_count


def scheduled_job(config):
    """
    Job function executed by scheduler.
    
    Args:
        config: List of AccountConfig objects
    """
    # Update timestamp for this execution cycle
    global _RUN_TIMESTAMP
    _RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("")
    logger.info("="*80)
    logger.info(f"⏰ Scheduled execution triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    run_all_accounts(config)
    
    logger.info("")
    logger.info(f"✅ Execution completed. Next run in {INTERVAL_MINUTES} minutes...")


def run_continuously(config):
    """
    Run accounts continuously at configured intervals using APScheduler.
    
    Args:
        config: List of AccountConfig objects
    """
    # Initialize orchestrator logger first
    init_orchestrator_logger()
    
    logger.info("="*80)
    logger.info("🚀 AI Futures Trading System - Scheduler Started")
    logger.info("="*80)
    logger.info(f"⏰ Schedule: Every {INTERVAL_MINUTES} minutes")
    logger.info(f"📋 Enabled accounts: {len([a for a in config if a.enabled])}")
    logger.info("🛑 Press Ctrl+C to stop")
    logger.info("="*80)
    
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Add job with interval trigger
    scheduler.add_job(
        func=scheduled_job,
        trigger=IntervalTrigger(minutes=INTERVAL_MINUTES),
        args=[config],
        id='trading_job',
        name='Trading Strategy Execution',
        replace_existing=True
    )
    
    # Run immediately on startup
    logger.info("🔥 Running initial execution...")
    scheduled_job(config)
    
    # Start scheduler (blocks until interrupted)
    try:
        logger.info("")
        logger.info("⏰ Scheduler started. Waiting for next execution...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.warning("\n⚠️  Shutdown signal received")
        scheduler.shutdown()
        logger.info("✅ Scheduler stopped gracefully")


def main():
    """Main entry point - runs continuously at configured intervals."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI Futures Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Use production config (default)
  python main.py --env dev    # Use development config
  python main.py --env prod   # Use production config
        """
    )
    parser.add_argument(
        "--env",
        type=str,
        default="prod",
        choices=["dev", "prod"],
        help="Environment to use (default: prod)"
    )
    args = parser.parse_args()
    
    # Determine config file based on environment
    config_file = f"config.{args.env}.yaml"
    
    # Check if config file exists
    if not Path(config_file).exists():
        logger.error(f"Config file not found: {config_file}")
        logger.info("Available config files:")
        for cfg in Path(".").glob("config.*.yaml"):
            logger.info(f"  - {cfg}")
        sys.exit(1)
    
    # Set environment variable so child processes know which config to use
    os.environ["CONFIG_FILE"] = config_file
    
    # Load config
    logger.info(f"Loading configuration from: {config_file}")
    config = load_config(config_file)
    
    # Run continuously
    run_continuously(config)


if __name__ == "__main__":
    # Required for multiprocessing on macOS/Windows
    multiprocessing.set_start_method('spawn', force=True)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
