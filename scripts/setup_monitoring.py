#!/usr/bin/env python3
"""Setup script for MESH monitoring infrastructure."""

from services.monitoring.logging import setup_structured_logging
from services.monitoring.metrics import get_metrics_collector
from services.monitoring.health import register_default_health_checks, get_health_checker
import asyncio
import logging
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


logger = logging.getLogger(__name__)


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(['docker', '--version'],
                                capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker not found")
            return False
    except FileNotFoundError:
        print("❌ Docker not found")
        return False


def check_docker_compose():
    """Check if Docker Compose is available."""
    try:
        result = subprocess.run(
            ['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker Compose found: {result.stdout.strip()}")
            return True
        else:
            # Try docker compose (newer syntax)
            result = subprocess.run(
                ['docker', 'compose', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker Compose found: {result.stdout.strip()}")
                return True
            else:
                print("❌ Docker Compose not found")
                return False
    except FileNotFoundError:
        print("❌ Docker Compose not found")
        return False


def create_directories():
    """Create necessary directories for monitoring."""
    directories = [
        "logs",
        "monitoring/prometheus/data",
        "monitoring/grafana/data",
        "monitoring/alertmanager/data"
    ]

    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")


def setup_permissions():
    """Set up proper permissions for monitoring directories."""
    try:
        # Grafana needs specific user permissions
        grafana_data = project_root / "monitoring/grafana/data"
        if grafana_data.exists():
            os.chmod(grafana_data, 0o755)

        # Prometheus data directory
        prometheus_data = project_root / "monitoring/prometheus/data"
        if prometheus_data.exists():
            os.chmod(prometheus_data, 0o755)

        print("✅ Set up directory permissions")

    except Exception as e:
        print(f"⚠️  Warning: Could not set permissions: {e}")


def start_monitoring_stack():
    """Start the monitoring stack using Docker Compose."""
    monitoring_dir = project_root / "monitoring"
    compose_file = monitoring_dir / "docker-compose.monitoring.yml"

    if not compose_file.exists():
        print(f"❌ Docker Compose file not found: {compose_file}")
        return False

    try:
        print("🚀 Starting monitoring stack...")

        # Change to monitoring directory
        os.chdir(monitoring_dir)

        # Start services
        result = subprocess.run([
            'docker-compose', '-f', 'docker-compose.monitoring.yml', 'up', '-d'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Monitoring stack started successfully")
            print("\n📊 Monitoring Services:")
            print("  - Prometheus: http://localhost:9090")
            print("  - Grafana: http://localhost:3000 (admin/admin)")
            print("  - Alertmanager: http://localhost:9093")
            print("  - Node Exporter: http://localhost:9100")
            return True
        else:
            print(f"❌ Failed to start monitoring stack: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error starting monitoring stack: {e}")
        return False
    finally:
        # Change back to project root
        os.chdir(project_root)


def stop_monitoring_stack():
    """Stop the monitoring stack."""
    monitoring_dir = project_root / "monitoring"
    compose_file = monitoring_dir / "docker-compose.monitoring.yml"

    if not compose_file.exists():
        print(f"❌ Docker Compose file not found: {compose_file}")
        return False

    try:
        print("🛑 Stopping monitoring stack...")

        # Change to monitoring directory
        os.chdir(monitoring_dir)

        # Stop services
        result = subprocess.run([
            'docker-compose', '-f', 'docker-compose.monitoring.yml', 'down'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Monitoring stack stopped successfully")
            return True
        else:
            print(f"❌ Failed to stop monitoring stack: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error stopping monitoring stack: {e}")
        return False
    finally:
        # Change back to project root
        os.chdir(project_root)


async def test_monitoring_services():
    """Test monitoring services."""
    print("🧪 Testing monitoring services...")

    try:
        # Set up structured logging
        setup_structured_logging(
            level="INFO",
            service_name="monitoring-test",
            enable_console=True
        )

        # Register health checks
        register_default_health_checks()
        health_checker = get_health_checker()

        # Test health checks
        print("  Testing health checks...")
        system_health = await health_checker.get_system_health()
        print(f"  System status: {system_health['status']}")
        print(f"  Total checks: {system_health['summary']['total_checks']}")
        print(f"  Healthy: {system_health['summary']['healthy']}")

        # Test metrics collection
        print("  Testing metrics collection...")
        metrics_collector = get_metrics_collector()

        # Record some test metrics
        metrics_collector.record_message_ingested("test", "success")
        metrics_collector.record_api_request("GET", "/test", 200)
        metrics_collector.set_connector_health("test", "test", True)

        # Get metrics
        metrics = metrics_collector.get_metrics()
        print(f"  Metrics collected: {len(metrics.split('\\n'))} lines")

        print("✅ Monitoring services test completed")
        return True

    except Exception as e:
        print(f"❌ Monitoring services test failed: {e}")
        return False


def show_status():
    """Show status of monitoring services."""
    monitoring_dir = project_root / "monitoring"
    compose_file = monitoring_dir / "docker-compose.monitoring.yml"

    if not compose_file.exists():
        print("❌ Monitoring stack not set up")
        return

    try:
        # Change to monitoring directory
        os.chdir(monitoring_dir)

        # Check service status
        result = subprocess.run([
            'docker-compose', '-f', 'docker-compose.monitoring.yml', 'ps'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("📊 Monitoring Stack Status:")
            print(result.stdout)
        else:
            print(f"❌ Failed to get status: {result.stderr}")

    except Exception as e:
        print(f"❌ Error getting status: {e}")
    finally:
        # Change back to project root
        os.chdir(project_root)


def main():
    """Main setup function."""
    print("🔧 MESH Monitoring Setup")
    print("=" * 50)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "start":
            if not check_docker() or not check_docker_compose():
                print("❌ Docker and Docker Compose are required")
                sys.exit(1)

            create_directories()
            setup_permissions()

            if start_monitoring_stack():
                print("\n🎉 Monitoring setup complete!")
                print("\nNext steps:")
                print("1. Wait a few seconds for services to start")
                print("2. Visit Grafana at http://localhost:3000")
                print(
                    "3. Import the dashboard configurations from monitoring/grafana/dashboards/")
                print("4. Start your MESH application to see metrics")
            else:
                sys.exit(1)

        elif command == "stop":
            stop_monitoring_stack()

        elif command == "status":
            show_status()

        elif command == "test":
            asyncio.run(test_monitoring_services())

        elif command == "restart":
            stop_monitoring_stack()
            if start_monitoring_stack():
                print("✅ Monitoring stack restarted")
            else:
                sys.exit(1)

        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: start, stop, status, test, restart")
            sys.exit(1)
    else:
        print("Available commands:")
        print("  start    - Start monitoring stack")
        print("  stop     - Stop monitoring stack")
        print("  status   - Show monitoring stack status")
        print("  test     - Test monitoring services")
        print("  restart  - Restart monitoring stack")
        print("\nExample: python scripts/setup_monitoring.py start")


if __name__ == "__main__":
    main()
