#!/usr/bin/env bash 

# This file executes after a VSCode dev container is created.

# Install application dependencies
pip install -r /workspace/dependencies/requirements.txt
# Install development dependencies
pip install -r /workspace/dependencies/dev-requirements.txt