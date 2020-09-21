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
@click.argument('db_conf', default=conf["database"])
@click.option('--verbose/--silent', default=False)
def resolve_script(batch_size, db_conf, verbose=False):
    db = prepare_db(**db_conf)
    skip = 0
    todo = count_and_log(db, batch_size, skip=skip)
    while todo:
        done, skip = resolve_loop(batch_size, db, todo, skip, verbose=verbose)
        db.client.indices.refresh(index=db.tweets)
        todo = count_and_log(db, batch_size, done=done, skip=skip)


if __name__ == '__main__':
    resolve_script()
