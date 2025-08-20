"""
Bridge process management and lifecycle control.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Optional YAML dependency
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .types import (
    BridgeConfig, BridgeInstance, BridgeStatus, BridgeType,
    MatrixBridgeHubError, BridgeConfigError
)

logger = logging.getLogger(__name__)


class BridgeManager:
    """
    Manages Matrix bridge processes and configurations.

    Handles starting/stopping bridge processes, monitoring their health,
    and managing their configuration files.
    """

    def __init__(self):
        self.bridge_instances: Dict[str, BridgeInstance] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False

    async def initialize(self) -> None:
        """Initialize bridge manager."""
        try:
            logger.info("Initializing bridge manager")

            # Start monitoring task
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_bridges())

            logger.info("Bridge manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize bridge manager: {e}")
            raise MatrixBridgeHubError(
                f"Bridge manager initialization failed: {e}")

    async def cleanup(self) -> None:
        """Cleanup bridge manager resources."""
        try:
            logger.info("Cleaning up bridge manager")

            # Stop monitoring
            self._monitoring = False
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None

            # Stop all bridges
            await self.stop_all_bridges()

            logger.info("Bridge manager cleaned up")

        except Exception as e:
            logger.error(f"Error cleaning up bridge manager: {e}")

    async def add_bridge(self, config: BridgeConfig) -> BridgeInstance:
        """Add a new bridge configuration."""
        try:
            logger.info(f"Adding bridge: {config.bridge_name}")

            # Validate configuration
            await self._validate_bridge_config(config)

            # Create bridge instance
            instance = BridgeInstance(config=config)
            self.bridge_instances[config.bridge_name] = instance

            # Generate configuration file
            await self._generate_bridge_config(config)

            logger.info(f"Bridge added: {config.bridge_name}")
            return instance

        except Exception as e:
            logger.error(f"Failed to add bridge {config.bridge_name}: {e}")
            raise MatrixBridgeHubError(f"Failed to add bridge: {e}")

    async def remove_bridge(self, bridge_name: str) -> None:
        """Remove a bridge configuration."""
        try:
            logger.info(f"Removing bridge: {bridge_name}")

            instance = self.bridge_instances.get(bridge_name)
            if not instance:
                raise MatrixBridgeHubError(f"Bridge not found: {bridge_name}")

            # Stop bridge if running
            if instance.status in [BridgeStatus.RUNNING, BridgeStatus.CONNECTED]:
                await self.stop_bridge(bridge_name)

            # Remove from instances
            del self.bridge_instances[bridge_name]

            logger.info(f"Bridge removed: {bridge_name}")

        except Exception as e:
            logger.error(f"Failed to remove bridge {bridge_name}: {e}")
            raise MatrixBridgeHubError(f"Failed to remove bridge: {e}")

    async def start_bridge(self, bridge_name: str) -> bool:
        """Start a specific bridge."""
        try:
            logger.info(f"Starting bridge: {bridge_name}")

            instance = self.bridge_instances.get(bridge_name)
            if not instance:
                raise MatrixBridgeHubError(f"Bridge not found: {bridge_name}")

            if instance.status == BridgeStatus.RUNNING:
                logger.warning(f"Bridge already running: {bridge_name}")
                return True

            # Update status
            instance.status = BridgeStatus.STARTING
            instance.restart_attempts = 0
            instance.last_error = None

            # Start bridge process
            success = await self._start_bridge_process(instance)

            if success:
                instance.status = BridgeStatus.RUNNING
                instance.start_time = datetime.now(timezone.utc)
                logger.info(f"Bridge started successfully: {bridge_name}")
            else:
                instance.status = BridgeStatus.ERROR
                logger.error(f"Failed to start bridge: {bridge_name}")

            return success

        except Exception as e:
            logger.error(f"Error starting bridge {bridge_name}: {e}")
            if bridge_name in self.bridge_instances:
                self.bridge_instances[bridge_name].status = BridgeStatus.ERROR
                self.bridge_instances[bridge_name].last_error = str(e)
            return False

    async def stop_bridge(self, bridge_name: str) -> bool:
        """Stop a specific bridge."""
        try:
            logger.info(f"Stopping bridge: {bridge_name}")

            instance = self.bridge_instances.get(bridge_name)
            if not instance:
                raise MatrixBridgeHubError(f"Bridge not found: {bridge_name}")

            if instance.status == BridgeStatus.STOPPED:
                logger.warning(f"Bridge already stopped: {bridge_name}")
                return True

            # Stop bridge process
            success = await self._stop_bridge_process(instance)

            if success:
                instance.status = BridgeStatus.STOPPED
                instance.pid = None
                instance.start_time = None
                logger.info(f"Bridge stopped successfully: {bridge_name}")
            else:
                instance.status = BridgeStatus.ERROR
                logger.error(f"Failed to stop bridge: {bridge_name}")

            return success

        except Exception as e:
            logger.error(f"Error stopping bridge {bridge_name}: {e}")
            if bridge_name in self.bridge_instances:
                self.bridge_instances[bridge_name].status = BridgeStatus.ERROR
                self.bridge_instances[bridge_name].last_error = str(e)
            return False

    async def restart_bridge(self, bridge_name: str) -> bool:
        """Restart a specific bridge."""
        try:
            logger.info(f"Restarting bridge: {bridge_name}")

            # Stop bridge
            await self.stop_bridge(bridge_name)

            # Wait a moment
            await asyncio.sleep(2)

            # Start bridge
            return await self.start_bridge(bridge_name)

        except Exception as e:
            logger.error(f"Error restarting bridge {bridge_name}: {e}")
            return False

    async def stop_all_bridges(self) -> None:
        """Stop all running bridges."""
        try:
            logger.info("Stopping all bridges")

            stop_tasks = []
            for bridge_name in list(self.bridge_instances.keys()):
                stop_tasks.append(self.stop_bridge(bridge_name))

            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)

            logger.info("All bridges stopped")

        except Exception as e:
            logger.error(f"Error stopping all bridges: {e}")

    async def get_bridge_status(self, bridge_name: str) -> Dict[str, Any]:
        """Get status information for a bridge."""
        try:
            instance = self.bridge_instances.get(bridge_name)
            if not instance:
                return {"status": "not_found", "bridge_name": bridge_name}

            status_data = {
                "bridge_name": bridge_name,
                "bridge_type": instance.config.bridge_type.value,
                "status": instance.status.value,
                "enabled": instance.config.enabled,
                "restart_attempts": instance.restart_attempts,
                "max_restart_attempts": instance.config.max_restart_attempts,
            }

            if instance.pid:
                status_data["pid"] = instance.pid

            if instance.start_time:
                status_data["start_time"] = instance.start_time.isoformat()
                uptime = (datetime.now(timezone.utc) -
                          instance.start_time).total_seconds()
                status_data["uptime_seconds"] = uptime

            if instance.last_status_check:
                status_data["last_status_check"] = instance.last_status_check.isoformat()

            if instance.last_error:
                status_data["last_error"] = instance.last_error

            return status_data

        except Exception as e:
            logger.error(f"Error getting bridge status: {e}")
            return {"status": "error", "bridge_name": bridge_name, "error": str(e)}

    async def get_all_bridge_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all bridges."""
        try:
            status_data = {}
            for bridge_name in self.bridge_instances.keys():
                status_data[bridge_name] = await self.get_bridge_status(bridge_name)
            return status_data

        except Exception as e:
            logger.error(f"Error getting all bridge status: {e}")
            return {}

    async def _validate_bridge_config(self, config: BridgeConfig) -> None:
        """Validate bridge configuration."""
        try:
            # Check required fields
            if not config.bridge_name:
                raise BridgeConfigError("Bridge name is required")

            if not config.executable_path:
                raise BridgeConfigError("Executable path is required")

            if not config.config_path:
                raise BridgeConfigError("Config path is required")

            if not config.homeserver_url:
                raise BridgeConfigError("Homeserver URL is required")

            if not config.access_token:
                raise BridgeConfigError("Access token is required")

            if not config.user_id:
                raise BridgeConfigError("User ID is required")

            # Check if executable exists
            if not os.path.exists(config.executable_path) and not self._is_in_path(config.executable_path):
                logger.warning(
                    f"Bridge executable not found: {config.executable_path}")

            # Create config directory if it doesn't exist
            config_dir = os.path.dirname(config.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(config.database_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

        except Exception as e:
            logger.error(f"Bridge config validation failed: {e}")
            raise BridgeConfigError(f"Config validation failed: {e}")

    def _is_in_path(self, executable: str) -> bool:
        """Check if executable is in PATH."""
        try:
            result = subprocess.run(
                ['which', executable], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    async def _generate_bridge_config(self, config: BridgeConfig) -> None:
        """Generate configuration file for bridge."""
        try:
            logger.debug(f"Generating config for {config.bridge_name}")

            if config.bridge_type == BridgeType.WHATSAPP:
                await self._generate_whatsapp_config(config)
            elif config.bridge_type == BridgeType.INSTAGRAM:
                await self._generate_instagram_config(config)
            elif config.bridge_type == BridgeType.LINKEDIN:
                await self._generate_linkedin_config(config)
            else:
                logger.warning(f"Unknown bridge type: {config.bridge_type}")

        except Exception as e:
            logger.error(
                f"Failed to generate config for {config.bridge_name}: {e}")
            raise BridgeConfigError(f"Config generation failed: {e}")

    async def _generate_whatsapp_config(self, config: BridgeConfig) -> None:
        """Generate mautrix-whatsapp configuration."""
        try:
            whatsapp_config = {
                'homeserver': {
                    'address': config.homeserver_url,
                    'domain': config.homeserver_url.replace('https://', '').replace('http://', ''),
                },
                'appservice': {
                    'address': 'http://localhost:29318',
                    'hostname': '0.0.0.0',
                    'port': 29318,
                    'database': {
                        'type': 'sqlite3',
                        'uri': config.database_path,
                    },
                    'id': 'whatsapp',
                    'bot': {
                        'username': 'whatsappbot',
                        'displayname': 'WhatsApp Bridge Bot',
                        'avatar': 'mxc://maunium.net/NeXNQarUbrlYBiPCpprYsRqr',
                    },
                    'as_token': config.access_token,
                    'hs_token': config.access_token,
                },
                'bridge': {
                    'username_template': 'whatsapp_{userid}',
                    'displayname_template': '{displayname} (WhatsApp)',
                    'personal_filtering_spaces': False,
                    'delivery_receipts': False,
                    'message_status_events': False,
                    'portal_message_buffer': 128,
                    'sync_direct_chat_list': False,
                    'double_puppet_server_map': {},
                    'double_puppet_allow_discovery': False,
                    'login_shared_secret_map': {},
                    'permissions': {
                        '*': 'relay',
                        config.homeserver_url.replace('https://', '').replace('http://', ''): 'user',
                        config.user_id: 'admin',
                    },
                },
                'whatsapp': {
                    'os_name': 'Mautrix-WhatsApp bridge',
                    'browser_name': 'unknown',
                },
                'logging': {
                    'version': 1,
                    'formatters': {
                        'colored': {
                            '()': 'mautrix.util.ColorFormatter',
                            'format': '[%(asctime)s] [%(levelname)s@%(name)s] %(message)s',
                        },
                        'normal': {
                            'format': '[%(asctime)s] [%(levelname)s@%(name)s] %(message)s',
                        },
                    },
                    'handlers': {
                        'file': {
                            'class': 'logging.handlers.RotatingFileHandler',
                            'formatter': 'normal',
                            'filename': './logs/whatsapp.log',
                            'maxBytes': 10485760,
                            'backupCount': 10,
                        },
                        'console': {
                            'class': 'logging.StreamHandler',
                            'formatter': 'colored',
                        },
                    },
                    'loggers': {
                        'mau': {
                            'level': 'DEBUG',
                        },
                        'whatsmeow': {
                            'level': 'DEBUG',
                        },
                    },
                    'root': {
                        'level': 'DEBUG',
                        'handlers': ['file', 'console'],
                    },
                },
            }

            # Write config file
            with open(config.config_path, 'w') as f:
                if HAS_YAML:
                    yaml.dump(whatsapp_config, f, default_flow_style=False)
                else:
                    json.dump(whatsapp_config, f, indent=2)
                    logger.warning(
                        "YAML library not available, using JSON format")

            logger.debug(f"Generated WhatsApp config: {config.config_path}")

        except Exception as e:
            logger.error(f"Failed to generate WhatsApp config: {e}")
            raise BridgeConfigError(f"WhatsApp config generation failed: {e}")

    async def _generate_instagram_config(self, config: BridgeConfig) -> None:
        """Generate mautrix-meta configuration for Instagram."""
        try:
            instagram_config = {
                'homeserver': {
                    'address': config.homeserver_url,
                    'domain': config.homeserver_url.replace('https://', '').replace('http://', ''),
                },
                'appservice': {
                    'address': 'http://localhost:29319',
                    'hostname': '0.0.0.0',
                    'port': 29319,
                    'database': {
                        'type': 'sqlite3',
                        'uri': config.database_path,
                    },
                    'id': 'instagram',
                    'bot': {
                        'username': 'instagrambot',
                        'displayname': 'Instagram Bridge Bot',
                        'avatar': 'mxc://maunium.net/JxjlbZUlCPULEeHZSwleUXQv',
                    },
                    'as_token': config.access_token,
                    'hs_token': config.access_token,
                },
                'bridge': {
                    'username_template': 'instagram_{userid}',
                    'displayname_template': '{displayname} (Instagram)',
                    'personal_filtering_spaces': False,
                    'portal_message_buffer': 128,
                    'sync_direct_chat_list': False,
                    'permissions': {
                        '*': 'relay',
                        config.homeserver_url.replace('https://', '').replace('http://', ''): 'user',
                        config.user_id: 'admin',
                    },
                },
                'meta': {
                    'mode': 'instagram',
                },
                'logging': {
                    'version': 1,
                    'formatters': {
                        'colored': {
                            '()': 'mautrix.util.ColorFormatter',
                            'format': '[%(asctime)s] [%(levelname)s@%(name)s] %(message)s',
                        },
                        'normal': {
                            'format': '[%(asctime)s] [%(levelname)s@%(name)s] %(message)s',
                        },
                    },
                    'handlers': {
                        'file': {
                            'class': 'logging.handlers.RotatingFileHandler',
                            'formatter': 'normal',
                            'filename': './logs/instagram.log',
                            'maxBytes': 10485760,
                            'backupCount': 10,
                        },
                        'console': {
                            'class': 'logging.StreamHandler',
                            'formatter': 'colored',
                        },
                    },
                    'loggers': {
                        'mau': {
                            'level': 'DEBUG',
                        },
                    },
                    'root': {
                        'level': 'DEBUG',
                        'handlers': ['file', 'console'],
                    },
                },
            }

            # Write config file
            with open(config.config_path, 'w') as f:
                if HAS_YAML:
                    yaml.dump(instagram_config, f, default_flow_style=False)
                else:
                    json.dump(instagram_config, f, indent=2)
                    logger.warning(
                        "YAML library not available, using JSON format")

            logger.debug(f"Generated Instagram config: {config.config_path}")

        except Exception as e:
            logger.error(f"Failed to generate Instagram config: {e}")
            raise BridgeConfigError(f"Instagram config generation failed: {e}")

    async def _generate_linkedin_config(self, config: BridgeConfig) -> None:
        """Generate mautrix-linkedin configuration."""
        try:
            linkedin_config = {
                'homeserver': {
                    'address': config.homeserver_url,
                    'domain': config.homeserver_url.replace('https://', '').replace('http://', ''),
                },
                'appservice': {
                    'address': 'http://localhost:29320',
                    'hostname': '0.0.0.0',
                    'port': 29320,
                    'database': {
                        'type': 'sqlite3',
                        'uri': config.database_path,
                    },
                    'id': 'linkedin',
                    'bot': {
                        'username': 'linkedinbot',
                        'displayname': 'LinkedIn Bridge Bot',
                        'avatar': 'mxc://maunium.net/LinkedInBridgeAvatar',
                    },
                    'as_token': config.access_token,
                    'hs_token': config.access_token,
                },
                'bridge': {
                    'username_template': 'linkedin_{userid}',
                    'displayname_template': '{displayname} (LinkedIn)',
                    'personal_filtering_spaces': False,
                    'portal_message_buffer': 128,
                    'sync_direct_chat_list': False,
                    'delivery_receipts': True,
                    'message_status_events': True,
                    'professional_context_awareness': True,  # LinkedIn-specific feature
                    'business_relationship_tracking': True,  # LinkedIn-specific feature
                    'permissions': {
                        '*': 'relay',
                        config.homeserver_url.replace('https://', '').replace('http://', ''): 'user',
                        config.user_id: 'admin',
                    },
                },
                'linkedin': {
                    'api_version': 'v2',
                    'messaging_scope': ['r_messaging', 'w_messaging'],
                    'profile_scope': ['r_basicprofile', 'r_contactinfo'],
                    'company_scope': ['r_organization_social'],
                    'professional_features': {
                        'extract_job_titles': True,
                        'extract_company_info': True,
                        'extract_industry_context': True,
                        'track_professional_relationships': True,
                        'identify_business_opportunities': True
                    },
                    'rate_limiting': {
                        'messages_per_hour': 100,
                        'api_calls_per_minute': 20
                    }
                },
                'logging': {
                    'version': 1,
                    'formatters': {
                        'colored': {
                            '()': 'mautrix.util.ColorFormatter',
                            'format': '[%(asctime)s] [%(levelname)s@%(name)s] %(message)s',
                        },
                        'normal': {
                            'format': '[%(asctime)s] [%(levelname)s@%(name)s] %(message)s',
                        },
                    },
                    'handlers': {
                        'file': {
                            'class': 'logging.handlers.RotatingFileHandler',
                            'formatter': 'normal',
                            'filename': './logs/linkedin.log',
                            'maxBytes': 10485760,
                            'backupCount': 10,
                        },
                        'console': {
                            'class': 'logging.StreamHandler',
                            'formatter': 'colored',
                        },
                    },
                    'loggers': {
                        'mau': {
                            'level': 'DEBUG',
                        },
                        'linkedin': {
                            'level': 'DEBUG',
                        },
                    },
                    'root': {
                        'level': 'DEBUG',
                        'handlers': ['file', 'console'],
                    },
                },
            }

            # Write config file
            with open(config.config_path, 'w') as f:
                if HAS_YAML:
                    yaml.dump(linkedin_config, f, default_flow_style=False)
                else:
                    json.dump(linkedin_config, f, indent=2)
                    logger.warning(
                        "YAML library not available, using JSON format")

            logger.debug(f"Generated LinkedIn config: {config.config_path}")

        except Exception as e:
            logger.error(f"Failed to generate LinkedIn config: {e}")
            raise BridgeConfigError(f"LinkedIn config generation failed: {e}")

    async def _start_bridge_process(self, instance: BridgeInstance) -> bool:
        """Start bridge process."""
        try:
            config = instance.config

            # Build command
            cmd = [config.executable_path, '-c', config.config_path]
            cmd.extend(config.extra_args)

            # Set up environment
            env = os.environ.copy()
            env.update(config.environment)

            # Start process
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )

            instance.process = process
            instance.pid = process.pid

            logger.info(
                f"Started bridge process {config.bridge_name} with PID {process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start bridge process: {e}")
            instance.last_error = str(e)
            return False

    async def _stop_bridge_process(self, instance: BridgeInstance) -> bool:
        """Stop bridge process."""
        try:
            if not instance.process:
                return True

            # Send SIGTERM
            try:
                os.killpg(os.getpgid(instance.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                # Process already terminated
                pass

            # Wait for graceful shutdown
            try:
                instance.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill
                try:
                    os.killpg(os.getpgid(instance.process.pid), signal.SIGKILL)
                    instance.process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    pass

            instance.process = None
            logger.info(
                f"Stopped bridge process {instance.config.bridge_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop bridge process: {e}")
            instance.last_error = str(e)
            return False

    async def _monitor_bridges(self) -> None:
        """Monitor bridge processes and restart if needed."""
        logger.info("Starting bridge monitoring")

        while self._monitoring:
            try:
                for bridge_name, instance in self.bridge_instances.items():
                    await self._check_bridge_health(instance)

                # Sleep between checks
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                logger.info("Bridge monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in bridge monitoring: {e}")
                await asyncio.sleep(5)

    async def _check_bridge_health(self, instance: BridgeInstance) -> None:
        """Check health of a bridge instance."""
        try:
            instance.last_status_check = datetime.now(timezone.utc)

            if not instance.process:
                if instance.status == BridgeStatus.RUNNING:
                    instance.status = BridgeStatus.STOPPED
                return

            # Check if process is still running
            poll_result = instance.process.poll()
            if poll_result is not None:
                # Process has terminated
                instance.status = BridgeStatus.STOPPED
                instance.process = None
                instance.pid = None

                logger.warning(
                    f"Bridge {instance.config.bridge_name} process terminated with code {poll_result}")

                # Auto-restart if enabled
                if (instance.config.auto_restart and
                    instance.config.enabled and
                        instance.restart_attempts < instance.config.max_restart_attempts):

                    logger.info(
                        f"Auto-restarting bridge {instance.config.bridge_name}")
                    instance.restart_attempts += 1

                    await asyncio.sleep(instance.config.restart_delay)
                    await self.start_bridge(instance.config.bridge_name)
            else:
                # Process is running
                if instance.status != BridgeStatus.RUNNING:
                    instance.status = BridgeStatus.RUNNING

        except Exception as e:
            logger.error(
                f"Error checking bridge health for {instance.config.bridge_name}: {e}")
            instance.last_error = str(e)
