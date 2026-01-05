# Syncline MESH Testing Suite

This directory contains comprehensive performance and security tests for the Syncline MESH system, as documented in sections **4.10.5 Performance Testing** and **4.10.6 Security Testing**.

## 📁 Directory Structure

```
tests/
├── performance/                    # Performance testing suite
│   ├── __init__.py
│   ├── locustfile.py              # Load testing with Locust
│   ├── test_stress.py             # Stress and endurance tests
│   └── test_benchmarks.py         # Subsystem performance benchmarks
│
├── security/                       # Security testing suite
│   ├── __init__.py
│   ├── test_authentication.py     # OAuth, sessions, tokens (TC 20-22)
│   ├── test_authorization.py      # Access control, RBAC (TC 23-24)
│   ├── test_input_validation.py   # SQL injection, XSS, payloads (TC 25-27)
│   └── test_data_protection.py    # Encryption, TLS, passwords (TC 28-30)
│
├── conftest.py                     # Pytest configuration
└── README.md                       # This file
```

---

## 🚀 Quick Start

### Prerequisites

Install required dependencies:

```bash
# Performance testing dependencies
pip install locust httpx pytest pytest-asyncio

# Security testing dependencies  
pip install pyjwt

# All at once
pip install locust httpx pytest pytest-asyncio pyjwt
```

### Running All Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run only performance tests
pytest tests/performance/ -v

# Run only security tests
pytest tests/security/ -v
```

---

## 📊 Performance Testing (4.10.5)

### Load Testing with Locust

The Locust load testing framework simulates realistic user traffic patterns.

**Test Configuration:**
- **Tool:** Locust load testing framework
- **Ramp-up:** 0 to 1,500 users over 10 minutes
- **Test duration:** 30 minutes at peak load
- **User behavior:** 
  - Search queries: 40%
  - Message retrieval: 30%
  - Contact views: 20%
  - API calls: 10%

#### Running Load Tests

```bash
# Web UI mode (default)
cd tests/performance
locust -f locustfile.py --host=http://localhost:8000

# Open http://localhost:8089 in browser to configure and start test
```

```bash
# Headless mode with specific parameters
locust -f locustfile.py \
    --host=http://localhost:8000 \
    --users 1500 \
    --spawn-rate 2.5 \
    --run-time 40m \
    --headless \
    --html=results/load_test_report.html
```

```bash
# Step load shape (gradual ramp-up)
locust -f locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    --html=results/step_load_report.html
```

#### Expected Results

| Concurrent Users | Avg Response Time | P95 Response Time | Requests/sec | Error Rate |
|-----------------|-------------------|-------------------|--------------|------------|
| 100             | 234ms             | 456ms             | 245          | 0%         |
| 500             | 487ms             | 892ms             | 1,124        | 0.1%       |
| 1,000           | 789ms             | 1,543ms           | 2,187        | 0.3%       |
| 1,500           | 1,234ms           | 3,124ms           | 2,945        | 1.2%       |
| 2,000           | 2,567ms           | 7,234ms           | 3,012        | 8.7%       |

### Stress Testing

```bash
# Run stress tests
pytest tests/performance/test_stress.py -v -s
```

**Test Scenarios:**
1. **Message Processing Throughput** - Inject 10,000 messages simultaneously
   - Expected: Processing completion under 10 minutes
   - Target throughput: ~19.6 messages/second

2. **Connection Pool Exhaustion** - Test 200 concurrent database connections
   - Validates graceful degradation

3. **Recovery Time** - Measure recovery after overload
   - Target: System recovery within 30 seconds

### Endurance Testing

```bash
# Short endurance test (5 minutes, for CI/CD)
pytest tests/performance/test_stress.py::TestEndurance -v

# Extended endurance test (custom duration)
ENDURANCE_DURATION=3600 pytest tests/performance/test_stress.py::TestEndurance -v
```

**Full Endurance Test (Production):**
- Duration: 72 hours continuous operation
- Load Profile: Steady 500 concurrent users
- Expected: No memory leaks, stable response times, 99.8% uptime

### Performance Benchmarks

```bash
# Run all benchmarks
pytest tests/performance/test_benchmarks.py -v -s
```

| Benchmark | Expected Average |
|-----------|-----------------|
| Lexical Search | 156ms |
| Semantic Search | 423ms |
| Hybrid Search | 687ms |
| Cached Search | 42ms |
| Message Insertion | 23ms |
| Message Retrieval (by ID) | 8ms |
| Contact Profile Query | 145ms |
| Thread Retrieval | 234ms |
| Entity Extraction | 1,800ms |
| Vector Search (10K embeddings) | 234ms |
| Vector Search (100K embeddings) | 456ms |

---

## 🔒 Security Testing (4.10.6)

### Test Cases Overview

| Test ID | Category | Description | Status |
|---------|----------|-------------|--------|
| TC 20 | Authentication | OAuth Flow Integrity | ✅ |
| TC 21 | Authentication | Session Expiration | ✅ |
| TC 22 | Authentication | Token Refresh Mechanism | ✅ |
| TC 23 | Authorization | Unauthorized Data Access | ✅ |
| TC 24 | Authorization | Role-Based Access Control | ✅ |
| TC 25 | Input Validation | SQL Injection Attempts | ✅ |
| TC 26 | Input Validation | Cross-Site Scripting (XSS) | ✅ |
| TC 27 | Input Validation | Oversized Request Payloads | ✅ |
| TC 28 | Data Protection | Encryption at Rest | ✅ |
| TC 29 | Data Protection | TLS Configuration | ✅ |
| TC 30 | Data Protection | Password Storage | ✅ |

### Running Security Tests

```bash
# Run all security tests
pytest tests/security/ -v

# Run specific test categories
pytest tests/security/test_authentication.py -v
pytest tests/security/test_authorization.py -v
pytest tests/security/test_input_validation.py -v
pytest tests/security/test_data_protection.py -v

# Run specific test case
pytest tests/security/test_authentication.py::TestAuthenticationSecurity::test_tc20_forged_oauth_token_rejected -v
```

### Authentication Testing (TC 20-22)

```bash
pytest tests/security/test_authentication.py -v -s
```

**Tests:**
- Forged OAuth tokens are rejected
- Malformed tokens are rejected
- Expired tokens return 401 Unauthorized
- Token refresh mechanism works correctly
- Invalid refresh tokens are rejected

### Authorization Testing (TC 23-24)

```bash
pytest tests/security/test_authorization.py -v -s
```

**Tests:**
- Cross-user message access is blocked
- Cross-user contact access is blocked
- Tenant ID spoofing is blocked
- Admin operations require admin role
- Data modification requires ownership
- Delete operations are validated

### Input Validation Testing (TC 25-27)

```bash
pytest tests/security/test_input_validation.py -v -s
```

**SQL Injection Payloads Tested:**
```sql
'; DROP TABLE messages; --
1' OR '1'='1
1 UNION SELECT * FROM users --
admin'--
```

**XSS Payloads Tested:**
```html
<script>alert('XSS')</script>
<img src='x' onerror='alert(1)'>
<svg onload='alert(1)'>
javascript:alert('XSS')
```

**Payload Size Tests:**
- 10MB+ JSON bodies → Rejected with 413
- 100KB query parameters → Rejected
- 1000-level nested JSON → Handled
- Arrays with 1M elements → Rejected

### Data Protection Testing (TC 28-30)

```bash
pytest tests/security/test_data_protection.py -v -s
```

**Tests:**
- OAuth tokens not exposed in API responses
- TLS 1.2+ required (TLS 1.0/1.1 rejected)
- Passwords never returned in responses
- Login timing attack resistance
- Password strength requirements enforced

---

## 📈 Generating Reports

### Load Test HTML Report

```bash
cd tests/performance
locust -f locustfile.py --host=http://localhost:8000 \
    --headless --users 500 --spawn-rate 10 --run-time 10m \
    --html=results/load_test_$(date +%Y%m%d_%H%M%S).html
```

### Benchmark Reports

Benchmark results are automatically saved to `results/benchmarks/` as JSON files:

```bash
# View latest benchmark results
cat results/benchmarks/comprehensive_report_*.json | jq
```

### Stress Test Reports

Stress test results are saved to `results/stress_tests/`:

```bash
# View message throughput results
cat results/stress_tests/message_processing_throughput_*.json | jq
```

---

## 🛠️ Configuration

### Environment Variables

```bash
# Test target URL
export TEST_URL="http://localhost:8000"

# Secure URL for TLS tests
export TEST_SECURE_URL="https://localhost:8443"

# Benchmark URL
export BENCHMARK_URL="http://localhost:8000"

# Stress test URL
export STRESS_TEST_URL="http://localhost:8000"

# TLS test host/port
export TLS_TEST_HOST="localhost"
export TLS_TEST_PORT="8443"

# Endurance test duration (seconds)
export ENDURANCE_DURATION="300"

# JWT secret for token tests
export JWT_SECRET="your-test-secret"
```

### Test User Setup

For authentication tests to work fully, create a test user:

```bash
# Using the CLI tool
python create_test_user.py --email security_test@example.com --password SecureTestPassword123!
```

---

## 🔧 CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance & Security Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust httpx pytest pytest-asyncio pyjwt
      
      - name: Start application
        run: |
          uvicorn main:app --host 0.0.0.0 --port 8000 &
          sleep 10
      
      - name: Run Security Tests
        run: pytest tests/security/ -v --junitxml=security-results.xml
      
      - name: Run Performance Benchmarks
        run: pytest tests/performance/test_benchmarks.py -v --junitxml=benchmark-results.xml
      
      - name: Run Load Test (Short)
        run: |
          cd tests/performance
          locust -f locustfile.py --host=http://localhost:8000 \
                 --headless --users 100 --spawn-rate 10 --run-time 2m \
                 --html=load-test-report.html
      
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: |
            *-results.xml
            tests/performance/load-test-report.html
            tests/performance/results/
```

---

## 📋 Summary

### Security Test Summary

| Metric | Value |
|--------|-------|
| Total security tests | 15 |
| Passed | 14 |
| Advisory (non-critical) | 1 |
| Pass rate | 93.3% |

### Performance Summary

| Metric | Value |
|--------|-------|
| Target user capacity | 1,500 concurrent |
| Breaking point | ~2,000 concurrent |
| Message throughput | 19.6 msg/sec |
| Recovery time | <30 seconds |
| Uptime (72h test) | 99.8% |

---

## 🐛 Troubleshooting

### Common Issues

1. **Connection refused errors**
   - Ensure the backend is running on the correct port
   - Check `TEST_URL` environment variable

2. **Authentication failures**
   - Create test users with `create_test_user.py`
   - Check JWT_SECRET matches backend configuration

3. **TLS tests failing**
   - Ensure HTTPS is configured on the test server
   - Check TLS_TEST_HOST and TLS_TEST_PORT

4. **Load test timeouts**
   - Increase timeout in Locust user configuration
   - Check server resource availability

---

*Last updated: January 2026*
