#!/bin/bash

if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SCRIPT_PATH="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    SCRIPT_PATH="${(%):-%N}"
else
    SCRIPT_PATH="$0"
fi

SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

load_secret_var() {
    local file_path="$1"
    local variable_name="$2"
    local variable_value

    if [ ! -f "$file_path" ]; then
        return
    fi

    variable_value=$(grep -E "^${variable_name}=" "$file_path" | tail -n 1)
    variable_value="${variable_value#*=}"

    if [ -n "$variable_value" ]; then
        export "$variable_name=$variable_value"
    fi
}

load_secret_var "$PROJECT_ROOT/.env.service-auth" "SERVICE_SECRET"
load_secret_var "$PROJECT_ROOT/.env.service-auth" "NODE_SERVICE_SECRET"

if [ -z "$SERVICE_SECRET" ] && [ -n "$NODE_SERVICE_SECRET" ]; then
    export SERVICE_SECRET="$NODE_SERVICE_SECRET"
fi
