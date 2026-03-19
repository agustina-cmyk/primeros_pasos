#!/bin/bash

# SDD — GitHub CLI Setup
# Detects OS, installs gh if missing, and runs auth login.
# Can be run standalone or called from sdd init.
#
# Exit codes:
#   0 = gh is installed and authenticated
#   1 = installation failed or user cancelled

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}SDD — GitHub CLI Setup${NC}"
echo ""

# --- Check if gh is already installed ---

if command -v gh &> /dev/null; then
    echo -e "${GREEN}✓ GitHub CLI (gh) is already installed${NC}"
    GH_VERSION=$(gh --version | head -n 1)
    echo "  ${GH_VERSION}"
    echo ""

    # Check auth status
    if gh auth status &> /dev/null; then
        echo -e "${GREEN}✓ Authenticated with GitHub${NC}"
        echo ""
        exit 0
    else
        echo -e "${YELLOW}! Not authenticated with GitHub${NC}"
        echo "  Running gh auth login..."
        echo ""
        gh auth login
        exit $?
    fi
fi

# --- gh not installed — detect OS and install ---

echo -e "${YELLOW}GitHub CLI (gh) is not installed.${NC}"
echo "  It's used by SDD to create pull requests directly from your terminal."
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ -f /etc/debian_version ]]; then
    OS="debian"
elif [[ -f /etc/redhat-release ]] || [[ -f /etc/fedora-release ]]; then
    OS="fedora"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Try to detect via package manager
    if command -v apt-get &> /dev/null; then
        OS="debian"
    elif command -v dnf &> /dev/null; then
        OS="fedora"
    fi
fi

case $OS in
    macos)
        echo "  Detected: macOS"
        if ! command -v brew &> /dev/null; then
            echo -e "${RED}✗ Homebrew is not installed${NC}"
            echo "  Install Homebrew first: https://brew.sh"
            echo "  Then run this script again."
            exit 1
        fi
        echo "  Installing via Homebrew..."
        echo ""
        brew install gh
        ;;
    debian)
        echo "  Detected: Debian/Ubuntu"
        echo "  Installing via apt..."
        echo ""
        (type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
            && sudo mkdir -p -m 755 /etc/apt/keyrings \
            && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
            && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
            && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
            && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
            && sudo apt update \
            && sudo apt install gh -y
        ;;
    fedora)
        echo "  Detected: Fedora/RHEL"
        echo "  Installing via dnf..."
        echo ""
        sudo dnf install 'dnf-command(config-manager)' -y
        sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
        sudo dnf install gh -y
        ;;
    *)
        echo -e "${RED}✗ Could not detect your OS automatically${NC}"
        echo ""
        echo "  Please install GitHub CLI manually:"
        echo "    https://github.com/cli/cli#installation"
        echo ""
        echo "  Then run this script again to authenticate."
        exit 1
        ;;
esac

# --- Verify installation ---

echo ""
if ! command -v gh &> /dev/null; then
    echo -e "${RED}✗ Installation failed. Please install manually:${NC}"
    echo "  https://github.com/cli/cli#installation"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI installed successfully${NC}"
GH_VERSION=$(gh --version | head -n 1)
echo "  ${GH_VERSION}"
echo ""

# --- Authenticate ---

echo "  Now let's authenticate with GitHub..."
echo ""
gh auth login
