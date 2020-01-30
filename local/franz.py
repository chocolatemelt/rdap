#!/usr/bin/env python3
from kafka import KafkaProducer
from kafka.errors import KafkaError
import sys

import config

def produce(filename):
    """Produces the contents of a file to a broker.

    Broker and topic are provided by config.py. The file is read line-by-line
    and sent directly to the brokers. A '>' is sent for each line read,
    mimicking the console producer provided by Kafka.

    Args:
        filename
            The path to a file containing data for ingestion.
    """
    producer = KafkaProducer(bootstrap_servers=config.kafka_brokers)
    with open(filename) as data:
            for line in data:
                sys.__stdout__.write('>')
                producer.send(config.kafka_topic, line.encode('ascii'))

if __name__ == '__main__':
    produce(sys.argv[1])
