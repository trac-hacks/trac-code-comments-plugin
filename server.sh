#!/bin/sh
tracd -s -r --port 8000 --basic-auth='trac,/Users/nb/sandbox/trac/htpasswd,R1' ~/sandbox/trac
