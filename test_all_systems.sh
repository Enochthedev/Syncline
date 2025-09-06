#!/bin/bash

# R.E.M.I Comprehensive System Test
# Tests all individual systems and provides a complete report

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${PURPLE}[HEADER]${NC} $1"; }

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    log_info "Running $test_name..."
    ((TOTAL_TESTS++))
    
    if eval "$test_command" >/dev/null 2>&1; then
        log_success "$test_name PASSED"
        ((PASSED_TESTS++))
        return 0
    else
        log_error "$test_name FAILED"
        ((FAILED_TESTS++))
        return 1
    fi
}

# Header
log_header "🚀 R.E.M.I Comprehensive System Test Suite"
log_header "=============================================="

# Test 1: Backend API
log_header "\n📡 Testing Backend API System"
run_test "Backend Core" "python test_backend_simple.py"

# Test 2: Mobile App
log_header "\n📱 Testing Mobile App System"
run_test "Mobile App Structure" "node test_mobile_simple.js"

# Test 3: Web App
log_header "\n🌐 Testing Web App System"
run_test "Web App Structure" "node test_web_simple.js"

# Test 4: Integration Services
log_header "\n🔗 Testing Integration Services"
run_test "Integration Services" "python test_integrations_simple.py"

# Test 5: Environment Check
log_header "\n🔧 Testing Environment"
run_test "Python Environment" "python --version"
run_test "Node.js Environment" "node --version"
run_test "NPM Environment" "npm --version"

# Test 6: File Structure
log_header "\n📁 Testing File Structure"
run_test "Backend Files" "test -f main.py && test -f requirements.txt"
run_test "Mobile Files" "test -d remi-mobile/src && test -f remi-mobile/package.json"
run_test "Web Files" "test -d remi-web/src && test -f remi-web/package.json"
run_test "Integration Files" "test -d integrations && test -f integrations/base_connector.py"

# Calculate score
SCORE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

# Final Report
log_header "\n📊 FINAL TEST REPORT"
log_header "===================="

echo -e "${BLUE}Total Tests:${NC} $TOTAL_TESTS"
echo -e "${GREEN}Passed:${NC} $PASSED_TESTS"
echo -e "${RED}Failed:${NC} $FAILED_TESTS"
echo -e "${PURPLE}Success Rate:${NC} $SCORE%"

if [ $SCORE -ge 80 ]; then
    log_success "🎉 SYSTEM READY FOR DEVELOPMENT!"
    echo -e "${GREEN}The R.E.M.I system is successfully integrated and ready to use.${NC}"
elif [ $SCORE -ge 60 ]; then
    log_warning "⚠️  SYSTEM MOSTLY READY"
    echo -e "${YELLOW}The system has minor issues but core functionality is working.${NC}"
else
    log_error "❌ SYSTEM NEEDS ATTENTION"
    echo -e "${RED}The system has significant issues that need to be resolved.${NC}"
fi

# Next Steps
log_header "\n🚀 NEXT STEPS"
echo "1. Start Backend API: python main.py"
echo "2. Start Mobile App: cd remi-mobile && npm run dev"
echo "3. Start Web App: cd remi-web && npm run dev"
echo "4. View Test Summary: cat system_test_summary.md"

# Exit with appropriate code
if [ $SCORE -ge 80 ]; then
    exit 0
else
    exit 1
fi