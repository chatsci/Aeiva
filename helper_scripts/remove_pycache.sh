#!/bin/bash

# Script to recursively remove all __pycache__ directories from a given path

# Make the script executable
# > chmod +x remove_pycache.sh

# Run the script
# > ./remove_pycache.sh /path/to/your/project

# Check if an argument was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory>"
    echo "Example: $0 /path/to/project"
    exit 1
fi

# Store the input directory
TARGET_DIR="$1"

# Check if the directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory '$TARGET_DIR' does not exist"
    exit 1
fi

# Convert to absolute path
TARGET_DIR=$(cd "$TARGET_DIR" && pwd)

echo "Searching for __pycache__ directories in: $TARGET_DIR"

# Find and count __pycache__ directories
COUNT=$(find "$TARGET_DIR" -type d -name "__pycache__" 2>/dev/null | wc -l)

if [ "$COUNT" -eq 0 ]; then
    echo "No __pycache__ directories found."
    exit 0
fi

echo "Found $COUNT __pycache__ directories:"
echo "-----------------------------------"

# List all __pycache__ directories that will be removed
find "$TARGET_DIR" -type d -name "__pycache__" -print 2>/dev/null

echo "-----------------------------------"
read -p "Do you want to remove all these directories? (y/N): " -n 1 -r
echo

if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    # Remove all __pycache__ directories
    find "$TARGET_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    echo "✓ Successfully removed all __pycache__ directories"
else
    echo "Operation cancelled"
    exit 0
fi