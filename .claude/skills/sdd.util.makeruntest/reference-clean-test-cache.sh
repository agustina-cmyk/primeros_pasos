#!/bin/bash

# Clean test cache and volumes
# Use this if you encounter issues with cached dependencies

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================="
echo "  Clean Test Cache & Volumes"
echo "================================================="
echo ""

echo -e "${YELLOW}This will remove:${NC}"
echo "  - Gradle cache volume (verification-api-gradle-cache)"
echo "  - Test Docker images"
echo "  - build directory (compiled classes)"
echo ""
echo -e "${YELLOW}Next test run will re-download dependencies${NC}"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Cleaning..."

# Get absolute path to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Remove Gradle cache volume
if docker volume inspect verification-api-gradle-cache &> /dev/null; then
    docker volume rm verification-api-gradle-cache
    echo -e "${GREEN}✓ Removed Gradle cache volume${NC}"
else
    echo "- Gradle cache volume not found (already clean)"
fi

# Remove test images
if docker images | grep -q "verification-api.*test"; then
    docker rmi $(docker images | grep "verification-api.*test" | awk '{print $3}') 2>/dev/null || true
    echo -e "${GREEN}✓ Removed test images${NC}"
else
    echo "- No test images found"
fi

# Remove build directory
if [ -d "${PROJECT_ROOT}/build" ]; then
    rm -rf "${PROJECT_ROOT}/build"
    echo -e "${GREEN}✓ Removed build directory${NC}"
else
    echo "- build directory not found"
fi

echo ""
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo ""
echo "Run './scripts/testing/run-tests.sh' to rebuild cache"
echo ""
