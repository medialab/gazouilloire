#!/usr/bin/env python
import click
from gazouilloire.config import create_conf_example, load_conf

@click.group()
def main():
    pass


@main.command()
@click.argument('path', type=click.Path(exists=True), default=".")
def init(path):
    create_conf_example(path)


@main.command()
@click.argument('path', type=click.Path(exists=True), default=".")
def run(path):
    conf = load_conf(path)
    raise NotImplementedError


@main.command()
def resolve():
    click.echo("resolve")
    raise NotImplementedError
