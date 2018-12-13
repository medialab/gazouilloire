#!/usr/bin/env python
# coding: utf8

from builtins import input
import click
from elasticsearch import Elasticsearch
from distutils.util import strtobool


@click.command()
@click.argument('es_index_name')
@click.argument('es_host', default='localhost')
@click.argument('es_port', default=9200)
def delete_index(es_host, es_port, es_index_name):
    es = Elasticsearch('http://%s:%s' % (es_host, es_port))

    tweets = es_index_name + '_tweets'
    links = es_index_name + '_links'

    if es.indices.exists(index=tweets):
        choice1 = strtobool(input(
            "Are you sure you want to delete " + tweets + "? (y/n) "))
        if choice1:
            es.indices.delete(index=tweets)
            print(">", tweets, "successfully deleted.")
    if es.indices.exists(index=links):
        choice2 = strtobool(input(
            "Are you sure you want to delete " + links + "? (y/n) "))
        if choice2:
            es.indices.delete(index=links)
            print(">", links, "successfully deleted.")


if __name__ == '__main__':
    delete_index()
