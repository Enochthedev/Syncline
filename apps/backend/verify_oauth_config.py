#!/usr/bin/env python3
"""
OAuth Configuration Verification Script

Verifies that Gmail and LinkedIn OAuth credentials are properly configured
and can be used for authentication.

Usage:
    python verify_oauth_config.py [--test-gmail] [--test-linkedin] [--all]

Example:
    python verify_oauth_config.py --all
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlencode

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# =============================================================================
# Configuration Check Functions
# =============================================================================


def check_env_var(var_name: str, required: bool = True) -> Tuple[bool, str]:
    """Check if environment variable is set and not a placeholder."""
    value = os.getenv(var_name)

    if not value:
        if required:
            return False, f"❌ {var_name}: Not set (required)"
        return True, f"⚪ {var_name}: Not set (optional)"

    # Check for placeholder values
    placeholders = [
        "your-",
        "your_",
        "placeholder",
        "change-this",
        "xxx",
        "XXXX",
        "example",
        "test-only",
    ]

    is_placeholder = any(p in value.lower() for p in placeholders)

    if is_placeholder:
        return False, f"⚠️  {var_name}: Contains placeholder value"

    # Mask the value for display
    masked = value[:4] + "..." + value[-4:] if len(value) > 12 else "****"
    return True, f"✅ {var_name}: {masked}"


def check_gmail_config() -> List[Tuple[bool, str]]:
    """Check Gmail OAuth configuration."""
    results = []

    print("\n" + "=" * 60)
    print("📧 Gmail OAuth Configuration Check")
    print("=" * 60)

    # Required variables
    required_vars = [
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
    ]

    # Optional but recommended
    optional_vars = [
        "GMAIL_REDIRECT_URI",
        "GMAIL_SCOPES",
        "GMAIL_WEBHOOK_URL",
        "GMAIL_WEBHOOK_SECRET",
    ]

    for var in required_vars:
        result = check_env_var(var, required=True)
        results.append(result)
        print(result[1])

    for var in optional_vars:
        result = check_env_var(var, required=False)
        results.append(result)
        print(result[1])

    # Check client ID format
    client_id = os.getenv("GMAIL_CLIENT_ID", "")
    if client_id and not client_id.endswith(".apps.googleusercontent.com"):
        print(f"⚠️  GMAIL_CLIENT_ID: Should end with '.apps.googleusercontent.com'")
        results.append((False, "Invalid client ID format"))

    return results


def check_linkedin_config() -> List[Tuple[bool, str]]:
    """Check LinkedIn OAuth configuration."""
    results = []

    print("\n" + "=" * 60)
    print("💼 LinkedIn OAuth Configuration Check")
    print("=" * 60)

    # Required variables
    required_vars = [
        "LINKEDIN_CLIENT_ID",
        "LINKEDIN_CLIENT_SECRET",
    ]

    # Optional but recommended
    optional_vars = [
        "LINKEDIN_REDIRECT_URI",
        "LINKEDIN_SCOPES",
    ]

    for var in required_vars:
        result = check_env_var(var, required=True)
        results.append(result)
        print(result[1])

    for var in optional_vars:
        result = check_env_var(var, required=False)
        results.append(result)
        print(result[1])

    return results


def generate_oauth_urls():
    """Generate OAuth authorization URLs for testing."""
    print("\n" + "=" * 60)
    print("🔗 OAuth Authorization URLs (for testing)")
    print("=" * 60)

    # Gmail OAuth URL
    gmail_client_id = os.getenv("GMAIL_CLIENT_ID")
    gmail_redirect_uri = os.getenv(
        "GMAIL_REDIRECT_URI", "http://localhost:8000/api/v1/connections/callback/gmail"
    )
    gmail_scopes = os.getenv(
        "GMAIL_SCOPES",
        "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.modify",
    )

    if gmail_client_id and "your-" not in gmail_client_id.lower():
        gmail_params = {
            "client_id": gmail_client_id,
            "redirect_uri": gmail_redirect_uri,
            "response_type": "code",
            "scope": gmail_scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": "test_state_gmail",
        }
        gmail_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(gmail_params)}"
        )
        print(f"\n📧 Gmail Authorization URL:")
        print(f"   {gmail_url[:100]}...")
    else:
        print("\n📧 Gmail: Cannot generate URL (client ID not configured)")

    # LinkedIn OAuth URL
    linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID")
    linkedin_redirect_uri = os.getenv(
        "LINKEDIN_REDIRECT_URI",
        "http://localhost:8000/api/v1/connections/callback/linkedin",
    )
    linkedin_scopes = os.getenv(
        "LINKEDIN_SCOPES", "r_liteprofile,r_emailaddress,w_member_social"
    )

    if linkedin_client_id and "your-" not in linkedin_client_id.lower():
        linkedin_params = {
            "response_type": "code",
            "client_id": linkedin_client_id,
            "redirect_uri": linkedin_redirect_uri,
            "scope": linkedin_scopes.replace(",", " "),
            "state": "test_state_linkedin",
        }
        linkedin_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(linkedin_params)}"
        print(f"\n💼 LinkedIn Authorization URL:")
        print(f"   {linkedin_url[:100]}...")
    else:
        print("\n💼 LinkedIn: Cannot generate URL (client ID not configured)")


async def test_gmail_token_endpoint():
    """Test Gmail token endpoint accessibility."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            # Test the actual OAuth2 token endpoint
            response = await client.get(
                "https://accounts.google.com/.well-known/openid-configuration",
                timeout=10.0,
            )
            if response.status_code == 200:
                print("✅ Gmail OAuth endpoint is accessible")
                return True
            else:
                print(f"⚠️  Gmail OAuth endpoint returned {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Gmail OAuth endpoint unreachable: {e}")
        return False


async def test_linkedin_token_endpoint():
    """Test LinkedIn token endpoint accessibility."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            # LinkedIn doesn't have a well-known endpoint, test the API base
            response = await client.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": "Bearer test"},
                timeout=10.0,
            )
            # 401 is expected (we're using an invalid token), but it means endpoint is up
            if response.status_code in [401, 403]:
                print("✅ LinkedIn API endpoint is accessible")
                return True
            else:
                print(f"⚠️  LinkedIn API endpoint returned {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ LinkedIn API endpoint unreachable: {e}")
        return False


def print_setup_instructions():
    """Print setup instructions for OAuth."""
    print("\n" + "=" * 60)
    print("📋 Setup Instructions")
    print("=" * 60)

    print("""
📧 Gmail Setup:
   1. Go to https://console.cloud.google.com/apis/credentials
   2. Create or select a project
   3. Click "Create Credentials" → "OAuth client ID"
   4. Select "Web application"
   5. Add authorized redirect URI:
      http://localhost:8000/api/v1/connections/callback/gmail
   6. Copy Client ID and Client Secret to .env

💼 LinkedIn Setup:
   1. Go to https://www.linkedin.com/developers/apps
   2. Click "Create app" or select existing
   3. Under "Auth" tab:
      - Copy Client ID and Client Secret
      - Add redirect URL:
        http://localhost:8000/api/v1/connections/callback/linkedin
   4. Under "Products" tab:
      - Request access to "Sign In with LinkedIn"
      - (Optional) Apply for Marketing Developer Platform for messaging
   5. Copy credentials to .env

⚠️  Important Notes:
   - Keep credentials secure, never commit them to git
   - LinkedIn Messaging API requires partnership approval
   - Gmail push notifications require a verified domain for production
""")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify OAuth configuration for Gmail and LinkedIn"
    )
    parser.add_argument(
        "--test-gmail", action="store_true", help="Test Gmail configuration"
    )
    parser.add_argument(
        "--test-linkedin", action="store_true", help="Test LinkedIn configuration"
    )
    parser.add_argument(
        "--all", action="store_true", help="Test all OAuth configurations"
    )
    parser.add_argument(
        "--urls", action="store_true", help="Generate OAuth authorization URLs"
    )
    parser.add_argument("--setup", action="store_true", help="Print setup instructions")
    parser.add_argument(
        "--connectivity", action="store_true", help="Test endpoint connectivity"
    )

    args = parser.parse_args()

    # Default to --all if no specific options given
    if not any(
        [
            args.test_gmail,
            args.test_linkedin,
            args.all,
            args.urls,
            args.setup,
            args.connectivity,
        ]
    ):
        args.all = True

    print("\n" + "🔐 OAuth Configuration Verification Tool".center(60))
    print("=" * 60)

    all_results = []

    if args.test_gmail or args.all:
        gmail_results = check_gmail_config()
        all_results.extend(gmail_results)

    if args.test_linkedin or args.all:
        linkedin_results = check_linkedin_config()
        all_results.extend(linkedin_results)

    if args.urls or args.all:
        generate_oauth_urls()

    if args.connectivity or args.all:
        print("\n" + "=" * 60)
        print("🌐 Endpoint Connectivity Check")
        print("=" * 60)
        asyncio.run(test_gmail_token_endpoint())
        asyncio.run(test_linkedin_token_endpoint())

    if args.setup:
        print_setup_instructions()

    # Summary
    passed = sum(1 for r in all_results if r[0])
    failed = sum(1 for r in all_results if not r[0])

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")

    if failed > 0:
        print(
            "\n⚠️  Some configuration issues found. Run with --setup for instructions."
        )
        return 1
    else:
        print("\n✅ All OAuth configurations look good!")
        return 0


if __name__ == "__main__":
    exit(main())
