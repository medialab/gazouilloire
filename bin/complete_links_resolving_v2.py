#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import click
from gazouilloire.url_resolve import resolve_loop, prepare_db, count_and_log

BATCH_SIZE = 1000
with open('config.json') as confile:
    conf = json.loads(confile.read())




@click.command()
@click.argument('batch_size', default=BATCH_SIZE)
@click.argument('host', default=conf["database"]["host"])
@click.argument('port', default=conf["database"]["port"])
@click.argument('db_name', default=conf["database"]["db_name"])
@click.option('--verbose/--silent', default=False)
def resolve_script(batch_size, host, port, db_name, verbose=False):
    db = prepare_db(host, port, db_name)
    skip = 0
    todo = count_and_log(db, batch_size, skip=skip)
    while todo:
        done, skip = resolve_loop(batch_size, db, todo, skip, verbose=verbose)
        todo = count_and_log(db, batch_size, done=done, skip=skip)


if __name__ == '__main__':
    resolve_script()
