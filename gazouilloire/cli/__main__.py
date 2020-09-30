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
@click.argument('path', type=click.Path(exists=True), default=".")
@click.argument('batch_size', default=1000)
@click.option('--verbose/--silent', default=False)
def resolve(path, batch_size, verbose):
    conf = load_conf(path)
    resolve_script(batch_size, **conf["database"], verbose=verbose)
