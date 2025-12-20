"""
Signup Automation - Main Entry Point
=====================================

Command-line interface for the signup automation framework.
Supports multiple platforms and execution modes.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from src.config import get_settings
from src.types.enums import Platform
from src.utils.logger import setup_logger, get_logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Multi-Platform Signup Automation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --platform airbnb
  python -m src.main --platform airbnb --batch 5
  python -m src.main --platform airbnb --all
  python -m src.main --platform airbnb --all --delay 15

Supported Platforms:
  - airbnb: Airbnb.com signup automation
        """,
    )

    parser.add_argument(
        "--platform",
        "-p",
        type=str,
        choices=["airbnb"],
        default="airbnb",
        help="Target platform for signup (default: airbnb)",
    )

    parser.add_argument(
        "--batch",
        "-b",
        type=int,
        default=1,
        help="Number of signup attempts (default: 1)",
    )

    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Run signup for ALL available phone numbers",
    )

    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Disable proxy usage",
    )

    parser.add_argument(
        "--delay",
        "-d",
        type=int,
        default=5,
        help="Delay between batch attempts in seconds (default: 5)",
    )

    parser.add_argument(
        "--phone-file",
        type=str,
        help="Path to phone numbers file (overrides config)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    return parser.parse_args()


async def run_airbnb(args: argparse.Namespace) -> None:
    """Run Airbnb signup automation."""
    from src.runners.airbnb_runner import run_single_signup, run_batch_signup, run_all_phones

    if args.all:
        await run_all_phones(delay_between=args.delay)
    elif args.batch > 1:
        await run_batch_signup(args.batch)
    else:
        await run_single_signup()


async def main_async(args: argparse.Namespace) -> int:
    """Async main function."""
    logger = get_logger("Main")

    logger.info(f"Starting signup automation for platform: {args.platform}")

    try:
        platform = Platform(args.platform)

        if platform == Platform.AIRBNB:
            await run_airbnb(args)
        else:
            logger.error(f"Platform not implemented: {platform}")
            return 1

        return 0

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logger()

    # Update settings based on args
    if args.verbose:
        import os
        os.environ["LOG_LEVEL"] = "DEBUG"

    # Run async main
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
