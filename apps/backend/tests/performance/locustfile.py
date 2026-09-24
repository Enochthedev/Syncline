"""
Locust Load Testing for Syncline MESH System

Test Configuration:
- Ramp-up: 0 to 1,500 users over 10 minutes
- Test duration: 30 minutes at peak load
- User behavior distribution:
  - Search queries: 40%
  - Message retrieval: 30%
  - Contact views: 20%
  - API calls: 10%

Run with:
    locust -f locustfile.py --host=http://localhost:8000

For headless mode with specific parameters:
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 1500 --spawn-rate 2.5 --run-time 40m \
           --headless --html=results/load_test_report.html
"""

import json
import os
import random
from datetime import datetime
from typing import Optional

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner, WorkerRunner

# Test data for realistic scenarios
SAMPLE_CONTACTS = [
    {"id": f"contact_{i}", "name": f"Contact {i}"} for i in range(1, 101)
]

SAMPLE_SEARCH_QUERIES = [
    "meeting tomorrow",
    "project update",
    "invoice payment",
    "schedule call",
    "document review",
    "follow up",
    "urgent request",
    "confirmation needed",
    "budget proposal",
    "team sync",
]

SAMPLE_MESSAGE_IDS = [f"msg_{i}" for i in range(1, 1001)]
SAMPLE_THREAD_IDS = [f"thread_{i}" for i in range(1, 201)]


class MESHUser(HttpUser):
    """
    Simulates a typical MESH user performing various operations.

    Task distribution (weighted):
    - Search: 40% (@task(4))
    - Messages: 30% (@task(3))
    - Contacts: 20% (@task(2))
    - API/Other: 10% (@task(1))
    """

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    # Auth token (set during login)
    token: Optional[str] = None
    user_id: Optional[str] = None

    def on_start(self):
        """Called when a simulated user starts."""
        self.login()

    def login(self):
        """Authenticate and obtain access token."""
        # For load testing, we use test credentials
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": f"loadtest_user_{random.randint(1, 1000)}@test.com",
                "password": "TestPassword123!",
            },
            name="/api/v1/auth/login",
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
        else:
            # Use a mock token for testing without real auth
            self.token = "test_token_for_load_testing"
            self.user_id = f"test_user_{random.randint(1, 1000)}"

    @property
    def auth_headers(self):
        """Return authorization headers."""
        return {"Authorization": f"Bearer {self.token}"}

    # ==========================================================================
    # SEARCH QUERIES (40% of traffic)
    # ==========================================================================

    @task(4)
    def search_messages(self):
        """Perform message search - 40% of traffic."""
        query = random.choice(SAMPLE_SEARCH_QUERIES)
        search_type = random.choice(["lexical", "semantic", "hybrid"])

        with self.client.get(
            "/api/v1/messages/search",
            params={
                "query": query,
                "search_type": search_type,
                "limit": 20,
                "offset": 0,
            },
            headers=self.auth_headers,
            name=f"/api/v1/messages/search [{search_type}]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Authentication failed")
            else:
                response.failure(f"Search failed: {response.status_code}")

    # ==========================================================================
    # MESSAGE RETRIEVAL (30% of traffic)
    # ==========================================================================

    @task(3)
    def get_messages(self):
        """Retrieve messages - 30% of traffic."""
        operation = random.choice(["list", "single", "thread"])

        if operation == "list":
            self._get_message_list()
        elif operation == "single":
            self._get_single_message()
        else:
            self._get_thread_messages()

    def _get_message_list(self):
        """Get paginated message list."""
        with self.client.get(
            "/api/v1/messages",
            params={
                "limit": 50,
                "offset": random.randint(0, 100),
                "platform": random.choice(["all", "whatsapp", "gmail", "slack"]),
            },
            headers=self.auth_headers,
            name="/api/v1/messages [list]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Message list failed: {response.status_code}")

    def _get_single_message(self):
        """Get a single message by ID."""
        message_id = random.choice(SAMPLE_MESSAGE_IDS)

        with self.client.get(
            f"/api/v1/messages/{message_id}",
            headers=self.auth_headers,
            name="/api/v1/messages/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:  # 404 is valid for test data
                response.success()
            else:
                response.failure(f"Message get failed: {response.status_code}")

    def _get_thread_messages(self):
        """Get messages in a thread."""
        thread_id = random.choice(SAMPLE_THREAD_IDS)

        with self.client.get(
            f"/api/v1/threads/{thread_id}",
            headers=self.auth_headers,
            name="/api/v1/threads/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Thread get failed: {response.status_code}")

    # ==========================================================================
    # CONTACT VIEWS (20% of traffic)
    # ==========================================================================

    @task(2)
    def view_contacts(self):
        """View contacts - 20% of traffic."""
        operation = random.choice(["list", "single", "profile"])

        if operation == "list":
            self._get_contact_list()
        elif operation == "single":
            self._get_single_contact()
        else:
            self._get_contact_profile()

    def _get_contact_list(self):
        """Get paginated contact list."""
        with self.client.get(
            "/api/v1/contacts",
            params={
                "limit": 25,
                "offset": random.randint(0, 50),
                "sort_by": random.choice(["name", "last_contact", "frequency"]),
            },
            headers=self.auth_headers,
            name="/api/v1/contacts [list]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Contact list failed: {response.status_code}")

    def _get_single_contact(self):
        """Get a single contact by ID."""
        contact = random.choice(SAMPLE_CONTACTS)

        with self.client.get(
            f"/api/v1/contacts/{contact['id']}",
            headers=self.auth_headers,
            name="/api/v1/contacts/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Contact get failed: {response.status_code}")

    def _get_contact_profile(self):
        """Get full contact profile with relationship metrics."""
        contact = random.choice(SAMPLE_CONTACTS)

        with self.client.get(
            f"/api/v1/contacts/{contact['id']}/profile",
            headers=self.auth_headers,
            name="/api/v1/contacts/{id}/profile",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Profile get failed: {response.status_code}")

    # ==========================================================================
    # API CALLS / OTHER OPERATIONS (10% of traffic)
    # ==========================================================================

    @task(1)
    def api_operations(self):
        """Misc API operations - 10% of traffic."""
        operation = random.choice(
            ["health_check", "connections_status", "stats", "ai_insights"]
        )

        if operation == "health_check":
            self._check_health()
        elif operation == "connections_status":
            self._get_connections()
        elif operation == "stats":
            self._get_stats()
        else:
            self._get_ai_insights()

    def _check_health(self):
        """Check API health status."""
        with self.client.get(
            "/api/v1/health", name="/api/v1/health", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    def _get_connections(self):
        """Get platform connection status."""
        with self.client.get(
            "/api/v1/connections",
            headers=self.auth_headers,
            name="/api/v1/connections",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Connections failed: {response.status_code}")

    def _get_stats(self):
        """Get user statistics."""
        with self.client.get(
            "/api/v1/stats/dashboard",
            headers=self.auth_headers,
            name="/api/v1/stats/dashboard",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Stats failed: {response.status_code}")

    def _get_ai_insights(self):
        """Get AI-generated insights."""
        with self.client.get(
            "/api/v1/ai/insights",
            headers=self.auth_headers,
            name="/api/v1/ai/insights",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"AI insights failed: {response.status_code}")


class StressTestUser(HttpUser):
    """
    User profile for stress testing - more aggressive than load testing.
    Simulates burst traffic patterns.
    """

    wait_time = between(0.1, 0.5)  # Very short wait times
    weight = 0  # Disabled by default, enable for stress tests

    def on_start(self):
        self.token = "stress_test_token"

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def rapid_search(self):
        """High-frequency search requests for stress testing."""
        self.client.get(
            "/api/v1/messages/search",
            params={"query": random.choice(SAMPLE_SEARCH_QUERIES), "limit": 50},
            headers=self.auth_headers,
            name="/api/v1/messages/search [stress]",
        )

    @task(5)
    def rapid_message_fetch(self):
        """High-frequency message retrieval."""
        self.client.get(
            "/api/v1/messages",
            params={"limit": 100, "offset": 0},
            headers=self.auth_headers,
            name="/api/v1/messages [stress]",
        )


# ==============================================================================
# EVENT HANDLERS FOR CUSTOM METRICS
# ==============================================================================


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics collection."""
    if isinstance(environment.runner, MasterRunner):
        print("Load test master initialized")
    elif isinstance(environment.runner, WorkerRunner):
        print("Load test worker initialized")

    # Create results directory
    os.makedirs("results", exist_ok=True)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print(f"\n{'='*60}")
    print(f"MESH Load Test Started")
    print(f"Target Host: {environment.host}")
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print(f"\n{'='*60}")
    print(f"MESH Load Test Completed")
    print(f"End Time: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # Export results summary
    stats = environment.stats
    results_summary = {
        "test_end_time": datetime.now().isoformat(),
        "total_requests": stats.total.num_requests,
        "total_failures": stats.total.num_failures,
        "average_response_time": stats.total.avg_response_time,
        "max_response_time": stats.total.max_response_time,
        "min_response_time": stats.total.min_response_time,
        "requests_per_second": stats.total.current_rps,
        "failures_per_second": stats.total.current_fail_per_sec,
    }

    with open("results/load_test_summary.json", "w") as f:
        json.dump(results_summary, f, indent=2)

    print(f"Results saved to results/load_test_summary.json")


# ==============================================================================
# CUSTOM SHAPE FOR RAMPING (Optional)
# ==============================================================================

from locust import LoadTestShape


class StepLoadShape(LoadTestShape):
    """
    A step load shape for gradual ramp-up testing.

    Ramps up users in steps to measure performance at each level:
    - Step 1: 100 users for 5 minutes
    - Step 2: 500 users for 5 minutes
    - Step 3: 1000 users for 10 minutes
    - Step 4: 1500 users for 10 minutes
    - Step 5: 2000 users for 5 minutes (breaking point test)
    """

    stages = [
        {"duration": 300, "users": 100, "spawn_rate": 10},  # 5 min @ 100 users
        {"duration": 600, "users": 500, "spawn_rate": 20},  # 5 min @ 500 users
        {"duration": 1200, "users": 1000, "spawn_rate": 25},  # 10 min @ 1000 users
        {"duration": 1800, "users": 1500, "spawn_rate": 25},  # 10 min @ 1500 users
        {"duration": 2100, "users": 2000, "spawn_rate": 30},  # 5 min @ 2000 users
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None  # Stop test
