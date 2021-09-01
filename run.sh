#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

#${SCRIPT_DIR}/retrieve_data.py
${SCRIPT_DIR}/move.py
${SCRIPT_DIR}/project_and_crop.sh
${SCRIPT_DIR}/mean_and_match.py
${SCRIPT_DIR}/generate_timelapse.py

echo "finished!"
