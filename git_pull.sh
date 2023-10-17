#!/bin/bash
cd /home/andy/realise/realise
GIT_BEFORE_PULL=$(git rev-parse HEAD)
git pull
GIT_AFTER_PULL=$(git rev-parse HEAD)

if [ "$GIT_BEFORE_PULL" != "$GIT_AFTER_PULL" ]; then
    /home/andy/realise/realise/start.sh
fi
