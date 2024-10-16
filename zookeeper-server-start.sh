#!/bin/sh
# Iniciar Zookeeper
KAFKA_HOME=""
$KAFKA_HOME/bin/zookeeper-server-start.sh $KAFKA_HOME/config/zookeeper.properties