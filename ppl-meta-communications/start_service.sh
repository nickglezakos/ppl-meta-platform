#!/bin/bash
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-communications
/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-communications/venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8009 --reload
