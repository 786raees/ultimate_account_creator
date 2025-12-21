"""
Airbnb Signup Runner
====================

Command-line runner for Airbnb signup automation.
Runs in a continuous loop, creating new MLX profiles for each signup.
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


async def no_otp_callback(phone: str) -> str:
    """
    No-op OTP callback - returns empty to trigger failure.

    When no OTP automation is configured, this immediately
    returns empty so the signup fails and moves to next number.

    Args:
        phone: The phone number (not used).

    Returns:
        Empty string to indicate no OTP available.
    """
    # No OTP automation - return empty to fail immediately
    return ""


async def manual_otp_callback(phone: str) -> str:
    """
    Manual OTP entry callback (for testing/debugging).

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


async def run_single_signup(use_manual_otp: bool = False) -> None:
    """
    Run a single Airbnb signup attempt.

    Args:
        use_manual_otp: If True, wait for manual OTP input. If False, fail at OTP step.
    """
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
    logger.info(f"Phone stats: {stats['available']} available, {stats['success']} success, {stats['failed']} failed")

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

    # Run signup - use manual OTP callback only if explicitly requested
    otp_cb = manual_otp_callback if use_manual_otp else None
    result = await orchestrator.run_single_signup(
        otp_callback=otp_cb
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


async def run_continuous_loop(delay_between: int = 10) -> None:
    """
    Run Airbnb signup in a continuous loop.

    Each iteration:
    1. Gets next available phone number
    2. Creates a new MLX profile
    3. Runs signup automation
    4. Closes profile
    5. Saves result (success/failed)
    6. Moves to next phone

    Args:
        delay_between: Delay between each signup attempt in seconds.
    """
    logger = get_logger("AirbnbRunner")
    settings = get_settings()

    print(f"\n{'='*60}")
    print("AIRBNB CONTINUOUS SIGNUP LOOP")
    print(f"{'='*60}")
    print("Each signup creates a fresh MLX profile")
    print(f"Delay between attempts: {delay_between}s")
    print(f"Success file: data/success.txt")
    print(f"Failed file: data/failed.txt")
    print(f"{'='*60}\n")

    # Initialize phone manager once
    phone_manager = PhoneManager(
        phone_list_path=settings.paths.phone_list_airbnb,
        state_path=settings.paths.used_phones_path,
        platform=Platform.AIRBNB,
    )
    await phone_manager.load()

    # Get initial stats
    stats = phone_manager.get_stats()
    total_available = stats['available']

    if total_available == 0:
        logger.error("No available phone numbers. Exiting.")
        return

    print(f"Starting with {total_available} available phone numbers\n")

    # Track results
    success_count = 0
    fail_count = 0
    attempt = 0

    # Run until no more phones available
    while True:
        # Re-check available count (file may have been modified)
        remaining = phone_manager.available_count

        if remaining == 0:
            print(f"\n{'='*60}")
            print("ALL PHONE NUMBERS PROCESSED")
            print(f"{'='*60}")
            break

        attempt += 1

        # Show which phone will be processed next
        next_phone = phone_manager.get_next()
        if not next_phone:
            print(f"\n{'='*60}")
            print("NO MORE PHONES AVAILABLE")
            print(f"{'='*60}")
            break

        print(f"\n{'='*60}")
        print(f"ATTEMPT {attempt} | {remaining} phones remaining")
        print(f"Next phone: {next_phone.formatted}")
        print(f"Success: {success_count} | Failed: {fail_count}")
        print(f"{'='*60}\n")

        # Initialize fresh data generator for each attempt
        data_generator = DataGenerator()

        # Initialize fresh orchestrator for each attempt
        # Each signup will create a new MLX profile automatically
        orchestrator = SignupOrchestrator(
            platform=Platform.AIRBNB,
            phone_manager=phone_manager,
            data_generator=data_generator,
        )

        try:
            # Run single signup (creates new MLX profile, runs, closes)
            # No OTP automation - but we check if OTP screen appears:
            #   - OTP screen appears = SUCCESS (phone is valid, SMS sent)
            #   - No OTP screen (captcha/error) = FAILED (phone rejected)
            result = await orchestrator.run_single_signup(
                otp_callback=None  # No OTP automation - just verify phone validity
            )

            if result.success:
                success_count += 1
                print(f"\n✓ SUCCESS #{success_count} - OTP SENT!")
                print(f"  Phone verified: OTP screen appeared")
                print(f"  (Phone number is valid, SMS was sent)")
                if result.account:
                    print(f"  Email: {result.account.email}")
                    print(f"  Phone: {result.account.phone}")
            else:
                fail_count += 1
                print(f"\n✗ FAILED #{fail_count} - NO OTP")
                print(f"  Error: {result.error_message}")
                print(f"  (Captcha, rate limit, or phone rejected)")
                print(f"  Step: {result.step_reached}")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user!")
            break

        except Exception as e:
            fail_count += 1
            logger.exception(f"Unexpected error during signup: {e}")
            print(f"\n✗ FAILED #{fail_count} (exception)")
            print(f"  Error: {e}")
            # Don't break - continue to next phone
            print("  Continuing to next phone...")

        # Wait before next attempt
        remaining = phone_manager.available_count
        if remaining > 0:
            print(f"\nWaiting {delay_between}s before next attempt...")
            await asyncio.sleep(delay_between)

    # Final summary
    total_processed = success_count + fail_count
    success_rate = (success_count / total_processed * 100) if total_processed > 0 else 0

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total Attempts: {total_processed}")
    print(f"OTP Sent (valid phones): {success_count}")
    print(f"Failed (captcha/rejected): {fail_count}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"\nResults saved to:")
    print(f"  Valid phones (OTP sent): data/success.txt")
    print(f"  Failed phones: data/failed.txt")
    print(f"{'='*60}\n")


async def run_all_phones(delay_between: int = 10) -> None:
    """
    Run Airbnb signup for ALL available phone numbers.
    Alias for run_continuous_loop for compatibility.

    Args:
        delay_between: Delay between each signup attempt in seconds.
    """
    await run_continuous_loop(delay_between=delay_between)


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

    results = []
    for i in range(count):
        print(f"\n{'='*50}")
        print(f"BATCH SIGNUP {i + 1}/{count}")
        print(f"{'='*50}")

        # Fresh orchestrator for each attempt
        orchestrator = SignupOrchestrator(
            platform=Platform.AIRBNB,
            phone_manager=phone_manager,
        )

        result = await orchestrator.run_single_signup(
            otp_callback=manual_otp_callback,
        )
        results.append(result)

        if i < count - 1:
            print(f"\nWaiting 10s before next attempt...")
            await asyncio.sleep(10)

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
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run signup for ALL available phone numbers (continuous loop)"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Same as --all: run continuous loop for all phones"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=10,
        help="Delay between attempts in seconds (default: 10)"
    )
    args = parser.parse_args()

    # Run appropriate mode
    if args.all or args.loop:
        asyncio.run(run_continuous_loop(delay_between=args.delay))
    elif args.batch > 0:
        asyncio.run(run_batch_signup(args.batch))
    else:
        asyncio.run(run_single_signup())


if __name__ == "__main__":
    main()
