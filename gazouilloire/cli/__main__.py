#!/usr/bin/env python
import click

@click.group()
def main():
    pass


@main.command()
@click.argument('path', type=click.Path(exists=True), default=".")
def init(path):
    click.echo("init " + path)


@main.command()
def run():
    click.echo("run")


@main.command()
def resolve():
    click.echo("resolve")