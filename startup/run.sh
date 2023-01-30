#!/bin/bash
# Not currently used (because windows)
DIR="$(dirname "$0")"
echo "Running vs-data-api from: $DIR"
cd "$DIR"
dotenv run -- uvicorn main:app --reload