#!/bin/bash
# Interactive PostgreSQL table browser
exec bash "$(dirname "$0")/setup_postgresql_interactive_v2.sh" --browse
