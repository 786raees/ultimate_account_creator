"""
Airbnb Signup Runner
====================

Command-line runner for Airbnb signup automation.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import get_settings
from src.services.signup_orchestrator import SignupOrchestrator
from src.types.enums import Platform
from src.utils.data_generator import DataGenerator
from src.utils.logger import setup_logger, get_logger
from src.utils.phone_manager import PhoneManager


async def manual_otp_callback(phone: str) -> str:
    """
    Manual OTP entry callback.

    Prompts user to enter the OTP code received on the phone.

    Args:
        phone: The phone number that received the OTP.

    Returns:
        The OTP code entered by the user.
    """
    print(f"\n{'='*50}")
    print(f"OTP REQUIRED for phone: {phone}")
    print(f"{'='*50}")

    # Use asyncio to handle input without blocking
    loop = asyncio.get_event_loop()
    otp = await loop.run_in_executor(
        None,
        lambda: input("Enter OTP code (or 'skip' to skip): ").strip()
    )

    if otp.lower() == 'skip':
        return ""

    return otp


async def run_single_signup() -> None:
    """Run a single Airbnb signup attempt."""
    logger = get_logger("AirbnbRunner")
    settings = get_settings()

    logger.info("Starting Airbnb signup runner")

    # Initialize phone manager
    phone_manager = PhoneManager(
        phone_list_path=settings.paths.phone_list_airbnb,
        state_path=settings.paths.used_phones_path,
        platform=Platform.AIRBNB,
    )
    await phone_manager.load()

    # Log phone stats
    stats = phone_manager.get_stats()
    logger.info(f"Phone stats: {stats['available']} available, {stats['used']} used")

    if stats['available'] == 0:
        logger.error("No available phone numbers. Exiting.")
        return

    # Initialize data generator
    data_generator = DataGenerator()

    # Initialize orchestrator
    orchestrator = SignupOrchestrator(
        platform=Platform.AIRBNB,
        phone_manager=phone_manager,
        data_generator=data_generator,
    )

    # Run signup
    result = await orchestrator.run_single_signup(
        otp_callback=manual_otp_callback
    )

    # Report result
    print(f"\n{'='*50}")
    print("SIGNUP RESULT")
    print(f"{'='*50}")
    print(f"Success: {result.success}")
    print(f"Platform: {result.platform}")
    print(f"Step Reached: {result.step_reached}")
    print(f"Duration: {result.duration_seconds:.2f} seconds")

    if result.success and result.account:
        print(f"\nAccount Created:")
        print(f"  Email: {result.account.email}")
        print(f"  Phone: {result.account.phone}")
        print(f"  Name: {result.account.profile.full_name}")
    elif result.error_message:
        print(f"\nError: {result.error_message}")

    print(f"{'='*50}\n")


async def run_batch_signup(count: int = 5) -> None:
    """
    Run multiple Airbnb signup attempts.

    Args:
        count: Number of signups to attempt.
    """
    logger = get_logger("AirbnbRunner")
    settings = get_settings()

    logger.info(f"Starting batch Airbnb signup: {count} attempts")

    # Initialize phone manager
    phone_manager = PhoneManager(
        phone_list_path=settings.paths.phone_list_airbnb,
        state_path=settings.paths.used_phones_path,
        platform=Platform.AIRBNB,
    )
    await phone_manager.load()

    # Check we have enough phones
    if phone_manager.available_count < count:
        logger.warning(
            f"Only {phone_manager.available_count} phones available "
            f"for {count} signups"
        )
        count = phone_manager.available_count

    if count == 0:
        logger.error("No available phone numbers. Exiting.")
        return

    # Initialize orchestrator
    orchestrator = SignupOrchestrator(
        platform=Platform.AIRBNB,
        phone_manager=phone_manager,
    )

    # Run batch
    results = await orchestrator.run_batch_signup(
        count=count,
        otp_callback=manual_otp_callback,
        delay_between=10,
    )

    # Summary
    successes = sum(1 for r in results if r.success)
    failures = count - successes

    print(f"\n{'='*50}")
    print("BATCH SIGNUP SUMMARY")
    print(f"{'='*50}")
    print(f"Total Attempts: {count}")
    print(f"Successful: {successes}")
    print(f"Failed: {failures}")
    print(f"Success Rate: {(successes/count)*100:.1f}%")

    if successes > 0:
        print(f"\nSuccessful Accounts:")
        for i, result in enumerate(results):
            if result.success and result.account:
                print(f"  {i+1}. {result.account.email} ({result.account.phone})")

    if failures > 0:
        print(f"\nFailed Attempts:")
        for i, result in enumerate(results):
            if not result.success:
                print(f"  {i+1}. Step: {result.step_reached}, Error: {result.error_message}")

    print(f"{'='*50}\n")


def main():
    """Main entry point for the Airbnb runner."""
    # Setup logging first
    setup_logger()

    # Parse command line args
    import argparse
    parser = argparse.ArgumentParser(
        description="Airbnb Signup Automation Runner"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=0,
        help="Number of signups to run in batch mode (0 for single)"
    )
    args = parser.parse_args()

    # Run appropriate mode
    if args.batch > 0:
        asyncio.run(run_batch_signup(args.batch))
    else:
        asyncio.run(run_single_signup())


if __name__ == "__main__":
    main()
