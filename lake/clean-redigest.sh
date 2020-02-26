#!/usr/bin/sh

./kafka_2.12-2.1.0/bin/kafka-topics.sh --zookeeper localhost:2181 --delete --topic rdap-lol
./kafka_2.12-2.1.0/bin/kafka-topics.sh --zookeeper localhost:2181 --create --replication-factor 1 --partitions 1 --topic rdap-lol

for data in ./data/*.json; do
	./franz.py "$data"
done
