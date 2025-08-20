#!/bin/bash

# MESH System Deployment Script
# Usage: ./scripts/deploy.sh [environment] [deployment-type]
# Example: ./scripts/deploy.sh production helm

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
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
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            if ! command -v docker &> /dev/null; then
                log_error "Docker is not installed"
                exit 1
            fi
            if ! command -v docker-compose &> /dev/null; then
                log_error "Docker Compose is not installed"
                exit 1
            fi
            ;;
        kubernetes)
            if ! command -v kubectl &> /dev/null; then
                log_error "kubectl is not installed"
                exit 1
            fi
            if ! kubectl cluster-info &> /dev/null; then
                log_error "Cannot connect to Kubernetes cluster"
                exit 1
            fi
            ;;
        helm)
            if ! command -v helm &> /dev/null; then
                log_error "Helm is not installed"
                exit 1
            fi
            if ! command -v kubectl &> /dev/null; then
                log_error "kubectl is not installed"
                exit 1
            fi
            if ! kubectl cluster-info &> /dev/null; then
                log_error "Cannot connect to Kubernetes cluster"
                exit 1
            fi
            ;;
        *)
            log_error "Unknown deployment type: $DEPLOYMENT_TYPE"
            log_info "Supported types: docker, kubernetes, helm"
            exit 1
            ;;
    esac
    
    log_success "Prerequisites check passed"
}

# Load environment configuration
load_environment() {
    log_info "Loading environment configuration for: $ENVIRONMENT"
    
    ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        source "$ENV_FILE"
        set +a
        log_success "Environment configuration loaded from $ENV_FILE"
    else
        log_warning "Environment file $ENV_FILE not found, using default .env"
        if [[ -f "$PROJECT_ROOT/.env" ]]; then
            set -a
            source "$PROJECT_ROOT/.env"
            set +a
        else
            log_error "No environment configuration found"
            exit 1
        fi
    fi
}

# Validate configuration
validate_configuration() {
    log_info "Validating configuration..."
    
    required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "POSTGRES_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "Configuration validation passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    services=("api" "worker" "ai-processor" "connectors")
    
    for service in "${services[@]}"; do
        log_info "Building $service image..."
        docker build -f "docker/Dockerfile.$service" -t "mesh-system/$service:latest" .
        if [[ $? -eq 0 ]]; then
            log_success "$service image built successfully"
        else
            log_error "Failed to build $service image"
            exit 1
        fi
    done
}

# Deploy with Docker Compose
deploy_docker() {
    log_info "Deploying with Docker Compose..."
    
    cd "$PROJECT_ROOT"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # Build images if needed
    if [[ "${BUILD_IMAGES:-true}" == "true" ]]; then
        build_images
    fi
    
    # Start services
    log_info "Starting services with $COMPOSE_FILE..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check health
    if curl -f "http://localhost:8000/api/v1/health" &> /dev/null; then
        log_success "API service is healthy"
    else
        log_error "API service health check failed"
        docker-compose -f "$COMPOSE_FILE" logs api
        exit 1
    fi
    
    log_success "Docker deployment completed successfully"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    cd "$PROJECT_ROOT"
    
    # Create namespace
    kubectl apply -f k8s/namespace.yaml
    
    # Apply configurations
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/storage.yaml
    
    # Deploy infrastructure
    log_info "Deploying infrastructure components..."
    kubectl apply -f k8s/postgres.yaml
    kubectl apply -f k8s/redis.yaml
    kubectl apply -f k8s/chromadb.yaml
    
    # Wait for infrastructure to be ready
    log_info "Waiting for infrastructure to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgres -n mesh-system --timeout=300s
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n mesh-system --timeout=300s
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=chromadb -n mesh-system --timeout=300s
    
    # Run database migrations
    log_info "Running database migrations..."
    kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: mesh-migration-$(date +%s)
  namespace: mesh-system
spec:
  template:
    spec:
      containers:
      - name: migration
        image: mesh-system/api:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mesh-secrets
              key: database-url
      restartPolicy: Never
  backoffLimit: 3
EOF
    
    # Deploy application services
    log_info "Deploying application services..."
    kubectl apply -f k8s/api.yaml
    kubectl apply -f k8s/worker.yaml
    kubectl apply -f k8s/ai-processor.yaml
    kubectl apply -f k8s/connectors.yaml
    
    # Deploy ingress
    kubectl apply -f k8s/ingress.yaml
    
    # Wait for application to be ready
    log_info "Waiting for application to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mesh-api -n mesh-system --timeout=300s
    
    log_success "Kubernetes deployment completed successfully"
}

# Deploy with Helm
deploy_helm() {
    log_info "Deploying with Helm..."
    
    cd "$PROJECT_ROOT"
    
    # Add required repositories
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo update
    
    # Create values file for environment
    VALUES_FILE="helm-values-$ENVIRONMENT.yaml"
    cat > "$VALUES_FILE" <<EOF
config:
  environment: $ENVIRONMENT
  logLevel: ${LOG_LEVEL:-INFO}

secrets:
  postgresPassword: $POSTGRES_PASSWORD
  databaseUrl: $DATABASE_URL
  gmail:
    clientId: ${GMAIL_CLIENT_ID:-}
    clientSecret: ${GMAIL_CLIENT_SECRET:-}
  slack:
    clientId: ${SLACK_CLIENT_ID:-}
    clientSecret: ${SLACK_CLIENT_SECRET:-}
  discord:
    botToken: ${DISCORD_BOT_TOKEN:-}
  twitter:
    apiKey: ${TWITTER_API_KEY:-}
    apiSecret: ${TWITTER_API_SECRET:-}
  telegram:
    botToken: ${TELEGRAM_BOT_TOKEN:-}
  openai:
    apiKey: ${OPENAI_API_KEY:-}
  anthropic:
    apiKey: ${ANTHROPIC_API_KEY:-}
  jwtSecretKey: ${JWT_SECRET_KEY:-change-me-in-production}
  encryptionKey: ${ENCRYPTION_KEY:-change-me-in-production}

ingress:
  enabled: true
  hosts:
    - host: ${MESH_DOMAIN:-mesh.localhost}
      paths:
        - path: /
          pathType: Prefix
EOF
    
    # Install or upgrade
    RELEASE_NAME="mesh-system-$ENVIRONMENT"
    NAMESPACE="mesh-system-$ENVIRONMENT"
    
    if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        log_info "Upgrading existing Helm release..."
        helm upgrade "$RELEASE_NAME" ./helm/mesh-system \
            --namespace "$NAMESPACE" \
            --values "$VALUES_FILE" \
            --wait --timeout=10m
    else
        log_info "Installing new Helm release..."
        helm install "$RELEASE_NAME" ./helm/mesh-system \
            --namespace "$NAMESPACE" \
            --create-namespace \
            --values "$VALUES_FILE" \
            --wait --timeout=10m
    fi
    
    # Clean up values file
    rm "$VALUES_FILE"
    
    log_success "Helm deployment completed successfully"
}

# Post-deployment verification
verify_deployment() {
    log_info "Verifying deployment..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            HEALTH_URL="http://localhost:8000/api/v1/health"
            ;;
        kubernetes|helm)
            # Get ingress URL or use port-forward
            if kubectl get ingress -n "mesh-system${ENVIRONMENT:+-$ENVIRONMENT}" &> /dev/null; then
                INGRESS_HOST=$(kubectl get ingress -n "mesh-system${ENVIRONMENT:+-$ENVIRONMENT}" -o jsonpath='{.items[0].spec.rules[0].host}')
                HEALTH_URL="https://$INGRESS_HOST/api/v1/health"
            else
                log_info "Setting up port-forward for health check..."
                kubectl port-forward -n "mesh-system${ENVIRONMENT:+-$ENVIRONMENT}" service/mesh-api-service 8080:8000 &
                PORT_FORWARD_PID=$!
                sleep 5
                HEALTH_URL="http://localhost:8080/api/v1/health"
            fi
            ;;
    esac
    
    # Health check with retries
    max_retries=10
    retry_count=0
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -f "$HEALTH_URL" &> /dev/null; then
            log_success "Health check passed"
            break
        else
            retry_count=$((retry_count + 1))
            log_warning "Health check failed, retrying... ($retry_count/$max_retries)"
            sleep 10
        fi
    done
    
    if [[ $retry_count -eq $max_retries ]]; then
        log_error "Health check failed after $max_retries attempts"
        exit 1
    fi
    
    # Clean up port-forward if used
    if [[ -n "${PORT_FORWARD_PID:-}" ]]; then
        kill $PORT_FORWARD_PID &> /dev/null || true
    fi
    
    # Additional verification
    log_info "Running additional verification checks..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            docker-compose ps
            ;;
        kubernetes|helm)
            kubectl get pods -n "mesh-system${ENVIRONMENT:+-$ENVIRONMENT}"
            kubectl get services -n "mesh-system${ENVIRONMENT:+-$ENVIRONMENT}"
            ;;
    esac
    
    log_success "Deployment verification completed successfully"
}

# Cleanup function
cleanup() {
    if [[ -n "${PORT_FORWARD_PID:-}" ]]; then
        kill $PORT_FORWARD_PID &> /dev/null || true
    fi
}

# Main deployment function
main() {
    log_info "Starting MESH System deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Deployment Type: $DEPLOYMENT_TYPE"
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    load_environment
    validate_configuration
    
    case $DEPLOYMENT_TYPE in
        docker)
            deploy_docker
            ;;
        kubernetes)
            deploy_kubernetes
            ;;
        helm)
            deploy_helm
            ;;
    esac
    
    verify_deployment
    
    log_success "MESH System deployment completed successfully!"
    log_info "Access the system at: $HEALTH_URL"
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