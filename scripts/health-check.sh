#!/bin/bash

# MESH System Health Check Script
# Usage: ./scripts/health-check.sh [environment] [deployment-type]

set -euo pipefail

# Configuration
ENVIRONMENT="${1:-development}"
DEPLOYMENT_TYPE="${2:-docker}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Health check results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to run a health check
run_check() {
    local check_name="$1"
    local check_command="$2"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    log_info "Checking: $check_name"
    
    if eval "$check_command" &> /dev/null; then
        log_success "$check_name"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        log_error "$check_name"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Docker health checks
check_docker_health() {
    log_info "Running Docker health checks..."
    
    run_check "Docker daemon" "docker info"
    run_check "Docker Compose services" "docker-compose ps | grep -q 'Up'"
    
    # Check individual services
    services=("postgres" "redis" "api" "worker" "ai-processor" "connectors")
    
    for service in "${services[@]}"; do
        run_check "Docker service: $service" "docker-compose ps $service | grep -q 'Up'"
    done
    
    # API health endpoint
    run_check "API health endpoint" "curl -f http://localhost:8000/api/v1/health"
    
    # Database connectivity
    run_check "Database connectivity" "docker-compose exec -T postgres pg_isready -U mesh_user"
    
    # Redis connectivity
    run_check "Redis connectivity" "docker-compose exec -T redis redis-cli ping | grep -q PONG"
}

# Kubernetes health checks
check_kubernetes_health() {
    log_info "Running Kubernetes health checks..."
    
    local namespace="mesh-system"
    if [[ "$ENVIRONMENT" != "production" ]]; then
        namespace="mesh-system-$ENVIRONMENT"
    fi
    
    run_check "Kubernetes cluster" "kubectl cluster-info"
    run_check "Namespace exists" "kubectl get namespace $namespace"
    
    # Check pods
    local pods=("postgres" "redis" "chromadb" "mesh-api" "mesh-worker" "mesh-ai-processor" "mesh-connectors")
    
    for pod in "${pods[@]}"; do
        run_check "Pod ready: $pod" "kubectl get pods -n $namespace -l app.kubernetes.io/name=$pod | grep -q Running"
    done
    
    # Check services
    local services=("postgres-service" "redis-service" "chromadb-service" "mesh-api-service")
    
    for service in "${services[@]}"; do
        run_check "Service exists: $service" "kubectl get service $service -n $namespace"
    done
    
    # API health endpoint
    if kubectl get ingress -n "$namespace" &> /dev/null; then
        local ingress_host
        ingress_host=$(kubectl get ingress -n "$namespace" -o jsonpath='{.items[0].spec.rules[0].host}')
        run_check "API health via ingress" "curl -f https://$ingress_host/api/v1/health"
    else
        # Use port-forward for health check
        kubectl port-forward -n "$namespace" service/mesh-api-service 8080:8000 &
        local port_forward_pid=$!
        sleep 5
        run_check "API health via port-forward" "curl -f http://localhost:8080/api/v1/health"
        kill $port_forward_pid &> /dev/null || true
    fi
}

# Helm health checks
check_helm_health() {
    log_info "Running Helm health checks..."
    
    local release_name="mesh-system-$ENVIRONMENT"
    local namespace="mesh-system-$ENVIRONMENT"
    
    run_check "Helm release exists" "helm list -n $namespace | grep -q $release_name"
    run_check "Helm release deployed" "helm status $release_name -n $namespace | grep -q 'STATUS: deployed'"
    
    # Run Kubernetes checks as well
    check_kubernetes_health
}

# Application-specific health checks
check_application_health() {
    log_info "Running application-specific health checks..."
    
    local base_url
    case $DEPLOYMENT_TYPE in
        docker)
            base_url="http://localhost:8000"
            ;;
        kubernetes|helm)
            local namespace="mesh-system"
            if [[ "$ENVIRONMENT" != "production" ]]; then
                namespace="mesh-system-$ENVIRONMENT"
            fi
            
            if kubectl get ingress -n "$namespace" &> /dev/null; then
                local ingress_host
                ingress_host=$(kubectl get ingress -n "$namespace" -o jsonpath='{.items[0].spec.rules[0].host}')
                base_url="https://$ingress_host"
            else
                kubectl port-forward -n "$namespace" service/mesh-api-service 8081:8000 &
                local port_forward_pid=$!
                sleep 5
                base_url="http://localhost:8081"
            fi
            ;;
    esac
    
    # API endpoints
    run_check "API root endpoint" "curl -f $base_url/"
    run_check "API health endpoint" "curl -f $base_url/api/v1/health"
    run_check "API stats endpoint" "curl -f $base_url/api/v1/stats"
    run_check "OpenAPI docs" "curl -f $base_url/docs"
    
    # GraphQL endpoint
    run_check "GraphQL endpoint" "curl -f -X POST $base_url/graphql -H 'Content-Type: application/json' -d '{\"query\":\"{ __schema { types { name } } }\"}'"
    
    # Clean up port-forward if used
    if [[ -n "${port_forward_pid:-}" ]]; then
        kill $port_forward_pid &> /dev/null || true
    fi
}

# Database health checks
check_database_health() {
    log_info "Running database health checks..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            # PostgreSQL checks
            run_check "PostgreSQL version" "docker-compose exec -T postgres psql -U mesh_user -d mesh_production -c 'SELECT version();'"
            run_check "Database tables exist" "docker-compose exec -T postgres psql -U mesh_user -d mesh_production -c '\\dt' | grep -q messages"
            run_check "Database connections" "docker-compose exec -T postgres psql -U mesh_user -d mesh_production -c 'SELECT count(*) FROM pg_stat_activity;'"
            
            # Redis checks
            run_check "Redis info" "docker-compose exec -T redis redis-cli info server | grep -q redis_version"
            run_check "Redis memory usage" "docker-compose exec -T redis redis-cli info memory | grep -q used_memory"
            ;;
        kubernetes|helm)
            local namespace="mesh-system"
            if [[ "$ENVIRONMENT" != "production" ]]; then
                namespace="mesh-system-$ENVIRONMENT"
            fi
            
            # PostgreSQL checks
            run_check "PostgreSQL version" "kubectl exec -n $namespace postgres-0 -- psql -U mesh_user -d mesh_production -c 'SELECT version();'"
            run_check "Database tables exist" "kubectl exec -n $namespace postgres-0 -- psql -U mesh_user -d mesh_production -c '\\dt' | grep -q messages"
            
            # Redis checks
            run_check "Redis info" "kubectl exec -n $namespace redis-0 -- redis-cli info server | grep -q redis_version"
            
            # ChromaDB checks
            run_check "ChromaDB heartbeat" "kubectl exec -n $namespace chromadb-0 -- curl -f http://localhost:8000/api/v1/heartbeat"
            ;;
    esac
}

# AI services health checks
check_ai_health() {
    log_info "Running AI services health checks..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            # Check if AI processor is running
            run_check "AI processor container" "docker-compose ps ai-processor | grep -q Up"
            
            # Check Ollama if enabled
            if docker-compose ps ollama | grep -q Up; then
                run_check "Ollama service" "curl -f http://localhost:11434/api/tags"
                run_check "Ollama models" "curl -s http://localhost:11434/api/tags | jq -r '.models[].name' | grep -q tinyllama"
            fi
            
            # Check ChromaDB
            run_check "ChromaDB service" "curl -f http://localhost:8004/api/v1/heartbeat"
            ;;
        kubernetes|helm)
            local namespace="mesh-system"
            if [[ "$ENVIRONMENT" != "production" ]]; then
                namespace="mesh-system-$ENVIRONMENT"
            fi
            
            # AI processor checks
            run_check "AI processor pods" "kubectl get pods -n $namespace -l app.kubernetes.io/name=mesh-ai-processor | grep -q Running"
            
            # ChromaDB checks
            run_check "ChromaDB pods" "kubectl get pods -n $namespace -l app.kubernetes.io/name=chromadb | grep -q Running"
            ;;
    esac
}

# Performance checks
check_performance() {
    log_info "Running performance checks..."
    
    local base_url
    case $DEPLOYMENT_TYPE in
        docker)
            base_url="http://localhost:8000"
            ;;
        kubernetes|helm)
            local namespace="mesh-system"
            if [[ "$ENVIRONMENT" != "production" ]]; then
                namespace="mesh-system-$ENVIRONMENT"
            fi
            
            if kubectl get ingress -n "$namespace" &> /dev/null; then
                local ingress_host
                ingress_host=$(kubectl get ingress -n "$namespace" -o jsonpath='{.items[0].spec.rules[0].host}')
                base_url="https://$ingress_host"
            else
                kubectl port-forward -n "$namespace" service/mesh-api-service 8082:8000 &
                local port_forward_pid=$!
                sleep 5
                base_url="http://localhost:8082"
            fi
            ;;
    esac
    
    # Response time check
    local response_time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' "$base_url/api/v1/health")
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        log_success "API response time: ${response_time}s"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warning "API response time slow: ${response_time}s"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    # Clean up port-forward if used
    if [[ -n "${port_forward_pid:-}" ]]; then
        kill $port_forward_pid &> /dev/null || true
    fi
}

# Security checks
check_security() {
    log_info "Running security checks..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            # Check for running containers with security issues
            run_check "No privileged containers" "! docker-compose ps | grep -q privileged"
            ;;
        kubernetes|helm)
            local namespace="mesh-system"
            if [[ "$ENVIRONMENT" != "production" ]]; then
                namespace="mesh-system-$ENVIRONMENT"
            fi
            
            # Check security contexts
            run_check "Pods not running as root" "! kubectl get pods -n $namespace -o jsonpath='{.items[*].spec.securityContext.runAsUser}' | grep -q '^0$'"
            run_check "Network policies exist" "kubectl get networkpolicy -n $namespace | grep -q mesh-network-policy"
            ;;
    esac
    
    # Check for exposed secrets (basic check)
    run_check "No secrets in environment" "! env | grep -i 'password\\|secret\\|key' | grep -v 'POSTGRES_PASSWORD\\|JWT_SECRET\\|ENCRYPTION_KEY'"
}

# Generate health report
generate_report() {
    echo ""
    echo "=================================="
    echo "    MESH System Health Report"
    echo "=================================="
    echo "Environment: $ENVIRONMENT"
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Timestamp: $(date)"
    echo ""
    echo "Results:"
    echo "  Total Checks: $TOTAL_CHECKS"
    echo "  Passed: $PASSED_CHECKS"
    echo "  Failed: $FAILED_CHECKS"
    echo ""
    
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        log_success "All health checks passed! System is healthy."
        echo "Status: HEALTHY"
        return 0
    else
        log_error "$FAILED_CHECKS out of $TOTAL_CHECKS checks failed."
        echo "Status: UNHEALTHY"
        return 1
    fi
}

# Main function
main() {
    log_info "Starting MESH System health check"
    log_info "Environment: $ENVIRONMENT"
    log_info "Deployment Type: $DEPLOYMENT_TYPE"
    echo ""
    
    # Run health checks based on deployment type
    case $DEPLOYMENT_TYPE in
        docker)
            check_docker_health
            ;;
        kubernetes)
            check_kubernetes_health
            ;;
        helm)
            check_helm_health
            ;;
        *)
            log_error "Unknown deployment type: $DEPLOYMENT_TYPE"
            exit 1
            ;;
    esac
    
    # Run common checks
    check_application_health
    check_database_health
    check_ai_health
    check_performance
    check_security
    
    # Generate final report
    generate_report
}

# Show usage if no arguments
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [environment] [deployment-type]"
    echo ""
    echo "Environments: development, staging, production"
    echo "Deployment Types: docker, kubernetes, helm"
    echo ""
    echo "Examples:"
    echo "  $0 development docker"
    echo "  $0 staging kubernetes"
    echo "  $0 production helm"
    exit 1
fi

# Run main function
main "$@"