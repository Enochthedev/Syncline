"""Rate limiting implementation for API endpoints."""

import logging
import time
from typing import Dict, Optional, Callable
from functools import wraps
from fastapi import HTTPException, status, Request
import redis
import json
from datetime import datetime, timedelta

from config.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis = None

    @property
    def redis(self):
        """Get Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        identifier: str = None
    ) -> tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed based on rate limit.

        Args:
            key: Rate limit key (e.g., "api:user:123", "api:ip:192.168.1.1")
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            identifier: Additional identifier for logging

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        try:
            current_time = int(time.time())
            window_start = current_time - window_seconds

            # Use Redis sorted set for sliding window
            pipe = self.redis.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(
                key, {f"{current_time}:{identifier or 'req'}": current_time})

            # Set expiration
            pipe.expire(key, window_seconds + 1)

            results = pipe.execute()
            current_count = results[1]

            # Check if limit exceeded
            is_allowed = current_count < limit

            if not is_allowed:
                # Remove the request we just added since it's not allowed
                self.redis.zrem(key, f"{current_time}:{identifier or 'req'}")

            rate_limit_info = {
                "limit": limit,
                "remaining": max(0, limit - current_count - (1 if is_allowed else 0)),
                "reset_time": current_time + window_seconds,
                "window_seconds": window_seconds
            }

            return is_allowed, rate_limit_info

        except Exception as e:
            logger.error(f"Rate limiting error for key {key}: {e}")
            # On error, allow the request (fail open)
            return True, {
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": int(time.time()) + window_seconds,
                "window_seconds": window_seconds
            }

    async def get_rate_limit_status(self, key: str, window_seconds: int) -> Dict[str, int]:
        """Get current rate limit status for a key."""
        try:
            current_time = int(time.time())
            window_start = current_time - window_seconds

            # Clean old entries and count current
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = pipe.execute()

            current_count = results[1]

            return {
                "current_count": current_count,
                "window_start": window_start,
                "window_end": current_time,
                "window_seconds": window_seconds
            }

        except Exception as e:
            logger.error(f"Error getting rate limit status for key {key}: {e}")
            return {
                "current_count": 0,
                "window_start": current_time - window_seconds,
                "window_end": current_time,
                "window_seconds": window_seconds
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    per_user: bool = True,
    per_ip: bool = False,
    per_tenant: bool = False
):
    """
    Rate limiting decorator for API endpoints.

    Args:
        requests_per_minute: Requests allowed per minute
        requests_per_hour: Requests allowed per hour
        per_user: Apply rate limit per authenticated user
        per_ip: Apply rate limit per IP address
        per_tenant: Apply rate limit per tenant
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and user from function arguments
            request = None
            current_user = None

            # Look for request in args/kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break

            # Look for user in kwargs
            for key, value in kwargs.items():
                if key in ['current_user', 'user'] and value:
                    current_user = value
                    break

            if not request:
                # If no request found, proceed without rate limiting
                return await func(*args, **kwargs)

            # Build rate limit keys
            rate_limit_keys = []

            if per_user and current_user:
                rate_limit_keys.append(f"rate_limit:user:{current_user.id}")

            if per_ip:
                client_ip = request.client.host if request.client else "unknown"
                rate_limit_keys.append(f"rate_limit:ip:{client_ip}")

            if per_tenant and current_user and hasattr(current_user, 'tenant_id'):
                rate_limit_keys.append(
                    f"rate_limit:tenant:{current_user.tenant_id}")

            # If no specific keys, use IP as fallback
            if not rate_limit_keys:
                client_ip = request.client.host if request.client else "unknown"
                rate_limit_keys.append(f"rate_limit:ip:{client_ip}")

            # Check rate limits
            rate_limit_info = {}

            for key in rate_limit_keys:
                # Check minute limit
                is_allowed_minute, info_minute = await rate_limiter.is_allowed(
                    f"{key}:minute",
                    requests_per_minute,
                    60,
                    str(current_user.id) if current_user else None
                )

                # Check hour limit
                is_allowed_hour, info_hour = await rate_limiter.is_allowed(
                    f"{key}:hour",
                    requests_per_hour,
                    3600,
                    str(current_user.id) if current_user else None
                )

                if not is_allowed_minute:
                    rate_limit_info = info_minute
                    rate_limit_info["limit_type"] = "per_minute"
                    break

                if not is_allowed_hour:
                    rate_limit_info = info_hour
                    rate_limit_info["limit_type"] = "per_hour"
                    break

                # Store the most restrictive limit info
                if not rate_limit_info or info_minute["remaining"] < rate_limit_info.get("remaining", float('inf')):
                    rate_limit_info = info_minute
                    rate_limit_info["limit_type"] = "per_minute"

            # If rate limit exceeded, raise HTTP exception
            if rate_limit_info.get("remaining", 1) <= 0:
                headers = {
                    "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_limit_info["reset_time"]),
                    "Retry-After": str(rate_limit_info["window_seconds"])
                }

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {rate_limit_info['limit']} requests per {rate_limit_info.get('limit_type', 'window')}",
                    headers=headers
                )

            # Add rate limit headers to response
            if hasattr(request, 'state'):
                request.state.rate_limit_info = rate_limit_info

            # Proceed with the original function
            return await func(*args, **kwargs)

        return wrapper
    return decorator


class TenantQuotaManager:
    """Manage per-tenant quotas and usage tracking."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis = None

    @property
    def redis(self):
        """Get Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def check_quota(
        self,
        tenant_id: str,
        resource: str,
        daily_limit: int,
        monthly_limit: int
    ) -> tuple[bool, Dict[str, int]]:
        """
        Check if tenant is within quota limits.

        Args:
            tenant_id: Tenant identifier
            resource: Resource type (e.g., 'api_calls', 'search_queries')
            daily_limit: Daily quota limit
            monthly_limit: Monthly quota limit

        Returns:
            Tuple of (within_quota, quota_info)
        """
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_month = datetime.now().strftime("%Y-%m")

            daily_key = f"quota:{tenant_id}:{resource}:daily:{current_date}"
            monthly_key = f"quota:{tenant_id}:{resource}:monthly:{current_month}"

            # Get current usage
            pipe = self.redis.pipeline()
            pipe.get(daily_key)
            pipe.get(monthly_key)
            results = pipe.execute()

            daily_usage = int(results[0] or 0)
            monthly_usage = int(results[1] or 0)

            # Check limits
            within_daily_quota = daily_usage < daily_limit
            within_monthly_quota = monthly_usage < monthly_limit
            within_quota = within_daily_quota and within_monthly_quota

            quota_info = {
                "daily_limit": daily_limit,
                "daily_usage": daily_usage,
                "daily_remaining": max(0, daily_limit - daily_usage),
                "monthly_limit": monthly_limit,
                "monthly_usage": monthly_usage,
                "monthly_remaining": max(0, monthly_limit - monthly_usage),
                "within_quota": within_quota
            }

            return within_quota, quota_info

        except Exception as e:
            logger.error(f"Quota check error for tenant {tenant_id}: {e}")
            # On error, allow the request (fail open)
            return True, {
                "daily_limit": daily_limit,
                "daily_usage": 0,
                "daily_remaining": daily_limit,
                "monthly_limit": monthly_limit,
                "monthly_usage": 0,
                "monthly_remaining": monthly_limit,
                "within_quota": True
            }

    async def increment_usage(
        self,
        tenant_id: str,
        resource: str,
        amount: int = 1
    ) -> Dict[str, int]:
        """Increment usage counters for tenant."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_month = datetime.now().strftime("%Y-%m")

            daily_key = f"quota:{tenant_id}:{resource}:daily:{current_date}"
            monthly_key = f"quota:{tenant_id}:{resource}:monthly:{current_month}"

            # Increment counters
            pipe = self.redis.pipeline()
            pipe.incrby(daily_key, amount)
            pipe.expire(daily_key, 86400)  # 24 hours
            pipe.incrby(monthly_key, amount)
            pipe.expire(monthly_key, 2678400)  # 31 days
            results = pipe.execute()

            return {
                "daily_usage": results[0],
                "monthly_usage": results[2]
            }

        except Exception as e:
            logger.error(f"Usage increment error for tenant {tenant_id}: {e}")
            return {"daily_usage": 0, "monthly_usage": 0}


# Global quota manager instance
quota_manager = TenantQuotaManager()
