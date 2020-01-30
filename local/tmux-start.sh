#!/bin/sh
#
# Sets up the druid-kafka tmux session `rdap` with three panes
# or attaches to an existing `rdap` session.

session="rdap"

# check if session exists and attach to it
tmux has -t $session 2>/dev/null
if [ $? == 0 ]; then
	tmux a -t $session
	exit 0
fi

# create a new tmux session
tmux new -d -s $session

# split across
tmux splitw -h -p 35

# select pane 1, start druid, split vertically
tmux selectp -t 1
tmux send-keys "./apache-druid-0.17.0/bin/start-micro-quickstart" C-m
tmux splitw -v -p 50

# select pane 2, start kafka
tmux selectp -t 2
tmux send-keys "./kafka_2.12-2.1.0/bin/kafka-server-start.sh ./kafka_2.12-2.1.0/config/server.properties" C-m

# select pane 1 and attach
tmux selectp -t 0
tmux attach-session -t $session
