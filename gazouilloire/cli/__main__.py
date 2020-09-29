#!/usr/bin/env python
import click


@click.command()
@click.argument('action', type=click.Choice(["init", "run", "resolve"], case_sensitive=False))
def main(action):
    click.echo(action)


