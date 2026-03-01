#!/bin/bash
# Docker Cleanup — Remove unused images, containers, volumes, and networks.
#
# Safely cleans up Docker resources to free disk space without
# removing running containers or tagged images in use.
#
# Usage:
#     ./docker_cleanup.sh                    # Interactive mode
#     ./docker_cleanup.sh --dry-run          # Preview what would be removed
#     ./docker_cleanup.sh --all              # Remove everything unused
#     ./docker_cleanup.sh --older-than 7d    # Only items older than 7 days
#
# No additional dependencies required.

set -euo pipefail

DRY_RUN=false
REMOVE_ALL=false
OLDER_THAN=""
VERBOSE=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run         Preview what would be removed"
    echo "  --all             Remove all unused resources"
    echo "  --older-than TIME Only remove items older than TIME (e.g., 24h, 7d)"
    echo "  --verbose         Show detailed output"
    echo "  --help            Show this help"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --all) REMOVE_ALL=true; shift ;;
        --older-than) OLDER_THAN="$2"; shift 2 ;;
        --verbose) VERBOSE=true; shift ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

prefix() {
    if $DRY_RUN; then
        echo "[DRY RUN]"
    else
        echo "[CLEANUP]"
    fi
}

echo "🐳 Docker Cleanup $(prefix)"
echo "================================"
echo ""

# Check Docker is running
if ! docker info &>/dev/null; then
    echo "❌ Docker is not running or not accessible"
    exit 1
fi

# Show current disk usage
echo "📊 Current Docker disk usage:"
docker system df 2>/dev/null || echo "  (df not available)"
echo ""

# --- Stopped Containers ---
STOPPED=$(docker ps -a -q --filter "status=exited" --filter "status=dead" --filter "status=created" 2>/dev/null | wc -l | tr -d ' ')
echo "📦 Stopped containers: $STOPPED"

if [[ $STOPPED -gt 0 ]]; then
    if $VERBOSE; then
        docker ps -a --filter "status=exited" --filter "status=dead" --filter "status=created" --format "  {{.ID}} {{.Names}} ({{.Status}})"
    fi
    
    if ! $DRY_RUN; then
        docker container prune -f ${OLDER_THAN:+--filter "until=$OLDER_THAN"} 2>/dev/null
        echo "  ✅ Removed"
    fi
fi

# --- Dangling Images ---
DANGLING=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l | tr -d ' ')
echo "🖼️  Dangling images: $DANGLING"

if [[ $DANGLING -gt 0 ]]; then
    if $VERBOSE; then
        docker images -f "dangling=true" --format "  {{.ID}} {{.Size}} (created {{.CreatedSince}})"
    fi
    
    if ! $DRY_RUN; then
        docker image prune -f 2>/dev/null
        echo "  ✅ Removed"
    fi
fi

# --- Unused Images (only with --all) ---
if $REMOVE_ALL; then
    UNUSED=$(docker images -q 2>/dev/null | wc -l | tr -d ' ')
    echo "🖼️  All unused images: $UNUSED"
    
    if ! $DRY_RUN; then
        docker image prune -a -f ${OLDER_THAN:+--filter "until=$OLDER_THAN"} 2>/dev/null
        echo "  ✅ Removed unused"
    fi
fi

# --- Unused Volumes ---
VOLUMES=$(docker volume ls -f "dangling=true" -q 2>/dev/null | wc -l | tr -d ' ')
echo "💾 Dangling volumes: $VOLUMES"

if [[ $VOLUMES -gt 0 ]]; then
    if $VERBOSE; then
        docker volume ls -f "dangling=true" --format "  {{.Name}}"
    fi
    
    if ! $DRY_RUN; then
        docker volume prune -f 2>/dev/null
        echo "  ✅ Removed"
    fi
fi

# --- Unused Networks ---
NETWORKS=$(docker network ls --filter "type=custom" -q 2>/dev/null | wc -l | tr -d ' ')
echo "🌐 Custom networks: $NETWORKS"

if ! $DRY_RUN; then
    docker network prune -f 2>/dev/null
    echo "  ✅ Pruned unused"
fi

# --- Build Cache ---
if $REMOVE_ALL; then
    echo "🔨 Build cache:"
    if ! $DRY_RUN; then
        docker builder prune -f ${OLDER_THAN:+--filter "until=$OLDER_THAN"} 2>/dev/null
        echo "  ✅ Cleared"
    fi
fi

echo ""
echo "📊 Disk usage after cleanup:"
docker system df 2>/dev/null || echo "  (df not available)"
echo ""
echo "$(prefix) Done! 🎉"
