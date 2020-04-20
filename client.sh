#!/bin/bash

export RALLY_DIR=$(pwd)
export PYTHONPATH=$(pwd)
cd client/client
/usr/bin/python3 $RALLY_DIR/client/client/client_main.py
