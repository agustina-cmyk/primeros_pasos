#!/bin/bash

# Optimized Test Runner for Verification API
# Uses Docker volumes to cache Gradle dependencies - MUCH faster on repeated runs!
# No image rebuilding, just runs tests directly in a container

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GRADLE_IMAGE="gradle:8.5-jdk17"
GRADLE_CACHE_VOLUME="verification-api-gradle-cache"
PROJECT_NAME="verification-api"

# Get absolute path to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "================================================="
echo "  Verification API - Fast Test Runner"
echo "  (Volume-cached strategy - super fast!)"
echo "================================================="
echo ""

# Function to print step headers
print_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Load GitHub Packages credentials from local.env if not already set
print_step "Step 1: Checking Prerequisites"

if [ -z "${USERNAME_TOKEN}" ] || [ -z "${PASSWORD_TOKEN}" ]; then
    ENV_FILE="${PROJECT_ROOT}/local.env"
    if [ -f "${ENV_FILE}" ]; then
        USERNAME_TOKEN=$(grep '^USERNAME_TOKEN=' "${ENV_FILE}" | cut -d'=' -f2-)
        PASSWORD_TOKEN=$(grep '^PASSWORD_TOKEN=' "${ENV_FILE}" | cut -d'=' -f2-)
        export USERNAME_TOKEN PASSWORD_TOKEN
        echo -e "${GREEN}✓ Loaded credentials from local.env${NC}"
    fi
fi

if [ -z "${USERNAME_TOKEN}" ] || [ -z "${PASSWORD_TOKEN}" ]; then
    echo -e "${RED}✗ Missing required environment variables${NC}"
    echo "  Set USERNAME_TOKEN and PASSWORD_TOKEN in local.env or export them"
    exit 1
fi
echo -e "${GREEN}✓ GitHub Packages credentials found${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"

# Create Gradle cache volume if it doesn't exist
if ! docker volume inspect ${GRADLE_CACHE_VOLUME} &> /dev/null; then
    echo -e "${YELLOW}Creating Gradle cache volume (one-time setup)...${NC}"
    docker volume create ${GRADLE_CACHE_VOLUME}
    echo -e "${GREEN}✓ Gradle cache volume created${NC}"
else
    echo -e "${GREEN}✓ Gradle cache volume exists${NC}"
fi

# Run tests in Docker with mounted volumes
print_step "Step 2: Running Tests"
echo "Strategy: Mount source code + cache dependencies in volume"
echo "This approach:"
echo "  ✓ Caches Gradle dependencies (fast on 2nd+ runs)"
echo "  ✓ No image rebuilding required"
echo "  ✓ Incremental compilation (Gradle handles it)"
echo ""
echo -e "${YELLOW}Running test suite...${NC}"
echo ""

START_TIME=$(date +%s)

# Run Gradle tests in container with volumes
# - Mount source code
# - Mount Gradle cache volume for dependencies
set +e  # Temporarily disable exit on error to capture exit code
docker run --rm \
    -e USERNAME_TOKEN="${USERNAME_TOKEN}" \
    -e PASSWORD_TOKEN="${PASSWORD_TOKEN}" \
    -v "${PROJECT_ROOT}:/app" \
    -v "${GRADLE_CACHE_VOLUME}:/home/gradle/.gradle" \
    -w /app \
    ${GRADLE_IMAGE} \
    gradle test --no-daemon

TEST_EXIT_CODE=$?
set -e  # Re-enable exit on error

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""

if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ All Tests Passed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Execution time: ${DURATION} seconds"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ Tests Failed${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Execution time: ${DURATION} seconds"
    echo "Check the output above for test failure details"
    echo ""
    exit 1
fi
