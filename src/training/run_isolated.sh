#!/bin/bash
# Isolate training process from terminal signals

# Trap and ignore SIGINT
trap '' INT

# Detach from terminal and run command
nohup "$@" </dev/null 2>&1 | cat
exit ${PIPESTATUS[0]}