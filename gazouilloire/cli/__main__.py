#!/usr/bin/env python
import click
from gazouilloire.config_format import create_conf_example, load_conf
from gazouilloire import run
from gazouilloire.resolving_script import resolve_script
from gazouilloire.exports.export_csv import export_csv


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


@main.command()
@click.argument('query', nargs=-1)
@click.option('--columns', '--select', '-c', '-s')
@click.option('--output', '-o', type=click.Path(exists=False))
@click.option('--path', '-p', type=click.Path(exists=True), default=".")
@click.option('--exclude_threads/--include_threads', default=False)
@click.option('--verbose/--quiet', default=True)
@click.option('--export_threads_from_file', '-f', type=click.Path(exists=True))
def export(path, query, exclude_threads, verbose, export_threads_from_file, columns, output):
    conf = load_conf(path)
    export_csv(conf, query, exclude_threads, verbose, export_threads_from_file, columns, output)