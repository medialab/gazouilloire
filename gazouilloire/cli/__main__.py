#!/usr/bin/env python
import click
from gazouilloire.config_format import create_conf_example, load_conf
from gazouilloire import run
from gazouilloire.resolving_script import resolve_script


@click.group()
def main():
    pass


@main.command()
@click.argument('path', type=click.Path(exists=True), default=".")
def init(path):
    create_conf_example(path)


@main.command()
@click.argument('path', type=click.Path(exists=True), default=".")
def start(path):
    conf = load_conf(path)
    run.main(conf)


@main.command()
@click.argument('db_name', required=True, type=str)
@click.argument('host', default="localhost")
@click.argument('port', default=9200)
@click.argument('batch_size', default=5000)
@click.option('--verbose/--silent', default=False)
def resolve(host, port, db_name, batch_size, verbose):
    resolve_script(batch_size, host, port, db_name, verbose=verbose)
