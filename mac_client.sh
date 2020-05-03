#!/bin/bash

export RALLY_DIR="$(pwd)"
echo "Rally dir: ${RALLY_DIR}"
echo "Python PATH: ${PYTHONPATH}"
export PYTHONPATH="$(pwd):${PYTHONPATH}"
echo "Python PATH: ${PYTHONPATH}"
cd client/client
python3 "$RALLY_DIR/client/client/client_main.py"
cd "${RALLY_DIR}"
