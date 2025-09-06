#!/bin/bash

# Comprehensive Test Runner for React Native App
# Runs all test suites with proper reporting and coverage

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_RESULTS_DIR="test-results"
COVERAGE_DIR="coverage"
REPORTS_DIR="reports"

# Create directories
mkdir -p $TEST_RESULTS_DIR
mkdir -p $COVERAGE_DIR
mkdir -p $REPORTS_DIR

echo -e "${BLUE}🧪 Starting Comprehensive Test Suite${NC}"
echo "========================================"

# Function to run test suite
run_test_suite() {
    local suite_name=$1
    local test_pattern=$2
    local description=$3
    
    echo -e "\n${YELLOW}📋 Running $description${NC}"
    echo "----------------------------------------"
    
    if npm run test -- $test_pattern --coverage --coverageDirectory="$COVERAGE_DIR/$suite_name" --testResultsProcessor="jest-junit" --outputFile="$TEST_RESULTS_DIR/$suite_name-results.xml"; then
        echo -e "${GREEN}✅ $description completed successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ $description failed${NC}"
        return 1
    fi
}

# Function to run E2E tests
run_e2e_tests() {
    echo -e "\n${YELLOW}🤖 Running End-to-End Tests${NC}"
    echo "----------------------------------------"
    
    # Build app for testing
    echo "Building app for E2E testing..."
    if npm run e2e:build:ios && npm run e2e:build:android; then
        echo -e "${GREEN}✅ App build completed${NC}"
    else
        echo -e "${RED}❌ App build failed${NC}"
        return 1
    fi
    
    # Run E2E tests
    if npm run e2e:ios && npm run e2e:android; then
        echo -e "${GREEN}✅ E2E tests completed successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ E2E tests failed${NC}"
        return 1
    fi
}

# Function to generate comprehensive report
generate_report() {
    echo -e "\n${BLUE}📊 Generating Comprehensive Test Report${NC}"
    echo "----------------------------------------"
    
    # Merge coverage reports
    npx nyc merge $COVERAGE_DIR $REPORTS_DIR/merged-coverage.json
    npx nyc report --reporter=html --reporter=lcov --reporter=text-summary --temp-dir=$REPORTS_DIR --report-dir=$REPORTS_DIR/coverage
    
    # Generate test summary
    cat > $REPORTS_DIR/test-summary.md << EOF
# Test Suite Summary

## Test Results

### Unit Tests
- **Status**: $([ -f "$TEST_RESULTS_DIR/unit-results.xml" ] && echo "✅ Passed" || echo "❌ Failed")
- **Coverage**: $(grep -o 'statements.*%' $REPORTS_DIR/coverage/lcov-report/index.html | head -1 || echo "N/A")

### Integration Tests
- **Status**: $([ -f "$TEST_RESULTS_DIR/integration-results.xml" ] && echo "✅ Passed" || echo "❌ Failed")

### Performance Tests
- **Status**: $([ -f "$TEST_RESULTS_DIR/performance-results.xml" ] && echo "✅ Passed" || echo "❌ Failed")

### Visual Regression Tests
- **Status**: $([ -f "$TEST_RESULTS_DIR/visual-results.xml" ] && echo "✅ Passed" || echo "❌ Failed")

### Security Tests
- **Status**: $([ -f "$TEST_RESULTS_DIR/security-results.xml" ] && echo "✅ Passed" || echo "❌ Failed")

### End-to-End Tests
- **Status**: $([ -f "$TEST_RESULTS_DIR/e2e-results.xml" ] && echo "✅ Passed" || echo "❌ Failed")

## Coverage Summary

$(cat $REPORTS_DIR/coverage/lcov-report/index.html | grep -A 5 "coverage-summary" || echo "Coverage data not available")

## Generated: $(date)
EOF

    echo -e "${GREEN}✅ Test report generated at $REPORTS_DIR/test-summary.md${NC}"
}

# Main test execution
main() {
    local exit_code=0
    
    # Run test suites
    run_test_suite "unit" "__tests__/unit" "Unit Tests" || exit_code=1
    run_test_suite "integration" "__tests__/integration" "Integration Tests" || exit_code=1
    run_test_suite "performance" "__tests__/performance" "Performance Tests" || exit_code=1
    run_test_suite "visual" "__tests__/visual" "Visual Regression Tests" || exit_code=1
    run_test_suite "security" "__tests__/security" "Security Tests" || exit_code=1
    
    # Run E2E tests if requested
    if [ "$1" = "--include-e2e" ]; then
        run_e2e_tests || exit_code=1
    fi
    
    # Generate comprehensive report
    generate_report
    
    # Final summary
    echo -e "\n${BLUE}📋 Test Suite Summary${NC}"
    echo "========================================"
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed successfully!${NC}"
        echo -e "📊 View detailed reports in: $REPORTS_DIR/"
        echo -e "📈 Coverage report: $REPORTS_DIR/coverage/index.html"
    else
        echo -e "${RED}💥 Some tests failed. Check the reports for details.${NC}"
        echo -e "📊 View detailed reports in: $REPORTS_DIR/"
    fi
    
    exit $exit_code
}

# Parse command line arguments
case "$1" in
    --unit)
        run_test_suite "unit" "__tests__/unit" "Unit Tests"
        ;;
    --integration)
        run_test_suite "integration" "__tests__/integration" "Integration Tests"
        ;;
    --performance)
        run_test_suite "performance" "__tests__/performance" "Performance Tests"
        ;;
    --visual)
        run_test_suite "visual" "__tests__/visual" "Visual Regression Tests"
        ;;
    --security)
        run_test_suite "security" "__tests__/security" "Security Tests"
        ;;
    --e2e)
        run_e2e_tests
        ;;
    --help)
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  --unit          Run unit tests only"
        echo "  --integration   Run integration tests only"
        echo "  --performance   Run performance tests only"
        echo "  --visual        Run visual regression tests only"
        echo "  --security      Run security tests only"
        echo "  --e2e           Run end-to-end tests only"
        echo "  --include-e2e   Run all tests including E2E"
        echo "  --help          Show this help message"
        echo ""
        echo "Default: Run all tests except E2E"
        ;;
    *)
        main "$@"
        ;;
esac