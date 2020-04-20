#!/bin/bash
export RALLY_DIR=$(pwd)
export PYTHONPATH=$(pwd)
cd server
/usr/bin/python3 $RALLY_DIR/server/server_main.py
