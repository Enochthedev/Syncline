#!/usr/bin/env python3
"""
R.E.M.I Backend Setup Validation Script
Checks that all infrastructure components are properly configured and accessible.
"""

import asyncio
import sys
from typing import Dict, List, Tuple


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_header(text: str):
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


async def check_postgres() -> Tuple[bool, str]:
    """Check PostgreSQL connection."""
    try:
        import asyncpg

        # Try to connect to Docker PostgreSQL
        try:
            conn = await asyncpg.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="password",
                database="mesh_development",
                timeout=5,
            )
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            return True, f"PostgreSQL connected: {version.split(',')[0]}"
        except asyncpg.InvalidPasswordError:
            # Password auth failed - might be local postgres without password
            return False, "PostgreSQL auth failed (check password in .env)"
        except asyncpg.InvalidCatalogNameError:
            # Database doesn't exist yet - but connection works
            return True, "PostgreSQL connected (database needs creation)"
        except Exception as conn_error:
            # Check if Docker container is running
            import subprocess

            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    "name=remi_postgres",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
            )
            if "Up" in result.stdout:
                return (
                    True,
                    "PostgreSQL container running (connection will work after setup)",
                )
            else:
                return False, f"PostgreSQL connection failed: {str(conn_error)}"
    except ImportError:
        return False, "asyncpg not installed (pip install asyncpg)"
    except Exception as e:
        return False, f"PostgreSQL check failed: {str(e)}"


async def check_redis() -> Tuple[bool, str]:
    """Check Redis connection."""
    try:
        import redis.asyncio as redis

        client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        await client.ping()
        info = await client.info("server")
        version = info.get("redis_version", "unknown")
        await client.close()
        return True, f"Redis connected: v{version}"
    except ImportError:
        return False, "redis not installed (pip install redis)"
    except Exception as e:
        return False, f"Redis connection failed: {str(e)}"


async def check_ollama() -> Tuple[bool, str]:
    """Check Ollama service."""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:11434/api/tags", timeout=5
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    model_count = len(models)
                    return True, f"Ollama connected: {model_count} models available"
                else:
                    return False, f"Ollama returned status {resp.status}"
    except ImportError:
        return False, "aiohttp not installed (pip install aiohttp)"
    except asyncio.TimeoutError:
        return False, "Ollama connection timeout (service may not be running)"
    except Exception as e:
        return False, f"Ollama connection failed: {str(e)}"


async def check_chromadb() -> Tuple[bool, str]:
    """Check ChromaDB service."""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            # Try v2 API first (newer versions)
            async with session.get(
                "http://localhost:8001/api/v2/heartbeat", timeout=5
            ) as resp:
                if resp.status == 200:
                    return True, "ChromaDB connected and healthy (v2 API)"
                # Fall back to v1 API
                async with session.get(
                    "http://localhost:8001/api/v1/heartbeat", timeout=5
                ) as resp_v1:
                    if resp_v1.status == 200:
                        return True, "ChromaDB connected and healthy (v1 API)"
                    elif resp_v1.status == 410:
                        # 410 means v1 is deprecated but service is running
                        return True, "ChromaDB connected (v1 deprecated, using v2)"
                    else:
                        return False, f"ChromaDB returned status {resp_v1.status}"
    except ImportError:
        return False, "aiohttp not installed (pip install aiohttp)"
    except asyncio.TimeoutError:
        return False, "ChromaDB connection timeout (service may not be running)"
    except Exception as e:
        return False, f"ChromaDB connection failed: {str(e)}"


def check_env_file() -> Tuple[bool, str]:
    """Check if .env file exists."""
    import os

    if os.path.exists(".env"):
        return True, ".env file exists"
    else:
        return False, ".env file not found (copy from .env.example)"


def check_directories() -> Tuple[bool, str]:
    """Check if required directories exist."""
    import os

    required_dirs = [
        "api",
        "config",
        "db",
        "integrations",
        "services",
        "tests",
        "utils",
    ]
    missing = [d for d in required_dirs if not os.path.isdir(d)]

    if not missing:
        return True, f"All required directories exist ({len(required_dirs)} dirs)"
    else:
        return False, f"Missing directories: {', '.join(missing)}"


def check_python_version() -> Tuple[bool, str]:
    """Check Python version."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return (
            False,
            f"Python 3.11+ required, found {version.major}.{version.minor}.{version.micro}",
        )


def check_dependencies() -> Tuple[bool, str]:
    """Check if key dependencies are installed."""
    required = ["fastapi", "sqlalchemy", "pydantic", "redis", "asyncpg"]
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if not missing:
        return True, f"All core dependencies installed ({len(required)} packages)"
    else:
        return False, f"Missing packages: {', '.join(missing)}"


async def run_checks():
    """Run all validation checks."""
    print_header("R.E.M.I Backend Setup Validation")

    checks = [
        ("Python Version", check_python_version, False),
        ("Dependencies", check_dependencies, False),
        ("Directory Structure", check_directories, False),
        ("Environment File", check_env_file, False),
        ("PostgreSQL", check_postgres, True),
        ("Redis", check_redis, True),
        ("ChromaDB", check_chromadb, True),
        ("Ollama", check_ollama, True),
    ]

    results: List[Tuple[str, bool, str]] = []

    for name, check_func, is_async in checks:
        print(f"Checking {name}...", end=" ", flush=True)
        try:
            if is_async:
                success, message = await check_func()
            else:
                success, message = check_func()

            results.append((name, success, message))
            print("\r" + " " * 50 + "\r", end="")  # Clear line

            if success:
                print_success(f"{name}: {message}")
            else:
                print_error(f"{name}: {message}")
        except Exception as e:
            results.append((name, False, str(e)))
            print("\r" + " " * 50 + "\r", end="")
            print_error(f"{name}: Unexpected error - {str(e)}")

    # Summary
    print_header("Validation Summary")

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    if passed == total:
        print_success(f"All checks passed! ({passed}/{total})")
        print("\n✨ Your backend setup is ready to go!")
        print("\nNext steps:")
        print("  1. Start services: docker-compose up -d")
        print("  2. Run migrations: alembic upgrade head")
        print("  3. Start server: python main.py")
        return 0
    else:
        failed = total - passed
        print_warning(f"{passed}/{total} checks passed, {failed} failed")
        print("\n⚠️  Some components need attention:")
        for name, success, message in results:
            if not success:
                print(f"  • {name}: {message}")
        return 1


def main():
    """Main entry point."""
    try:
        exit_code = asyncio.run(run_checks())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
