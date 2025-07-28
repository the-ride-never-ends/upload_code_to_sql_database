#!/bin/bash

# Function to display usage information
show_usage() {
    echo "Usage: $0 <directory> [options]"
    echo ""
    echo "Arguments:"
    echo "  directory               Directory path to scan for code files"
    echo ""
    echo "Options:"
    echo "  -r, --recursive         Scan directories recursively"
    echo "  -n, --dry-run          Perform a dry run without uploading to database"
    echo "  -e, --exclude PATTERN  Exclude files/directories matching pattern (can be used multiple times)"
    echo "  --db-config FILE       Path to database configuration file"
    echo "  -v, --verbose          Enable verbose output"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/project"
    echo "  $0 . --recursive --dry-run"
    echo "  $0 /project --exclude \"*.log\" --db-config db.conf --verbose"
}

# Check if no arguments provided or help requested
if [ $# -eq 0 ] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_usage
    exit 0
fi

# Echo to indicate start of the program
echo "STARTING PROGRAM..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment (.venv) not found!"
    echo "Please create a virtual environment first with: python -m venv .venv"
    exit 1
fi


# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

# Check if .env file exists before sourcing
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    # Import .env variables
    set -a
    source .env
    set +a
    echo "Environment variables loaded successfully."
else
    echo "ERROR: .env file not found."
    exit 1
fi


# Echo to indicate the start of the Python script
echo "*** BEGIN PROGRAM ***"


# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found in current directory!"
    deactivate
    exit 1
fi

# Run the Python script with all provided arguments
echo "Running Python script with arguments: $@"
python main.py "$@"

# Capture the exit code from the Python script
python_exit_code=$?

# Echo to indicate the end of the Python script
echo "*** END PROGRAM ***"
echo "Python script exit code: $python_exit_code"

# Deactivate the virtual environment
deactivate

# Echo to indicate program completion
if [ $python_exit_code -eq 0 ]; then
    echo "PROGRAM EXECUTION COMPLETE - SUCCESS"
else
    echo "PROGRAM EXECUTION COMPLETE - ERROR (exit code: $python_exit_code)"
fi

# Exit with the same code as the Python script
exit $python_exit_code
