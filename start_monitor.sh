#!/bin/bash
cd /home/ayan/dev/Monitor_ayan
nohup /home/ayan/dev/Monitor_ayan/venv/bin/python3 main.py >> logs/monitor_stdout.log 2>&1 &
echo "Monitor started in background. PID: $!"
