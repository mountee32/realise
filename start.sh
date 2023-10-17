#!/bin/bash
cd /home/andy/realise
pkill -f conversation.py  # Kills the previous instance if any
pkill -f message.py       # Kills the previous instance if any
uvicorn conversation:app --host 0.0.0.0 --port 8001 --reload &  # Reload flag ensures that it watches for changes
uvicorn message:app --host 0.0.0.0 --port 8002 --reload &
