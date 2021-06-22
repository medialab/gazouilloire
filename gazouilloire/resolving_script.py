#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from gazouilloire.url_resolve import resolve_loop, count_and_log
from gazouilloire.database.elasticmanager import prepare_db
from gazouilloire.config_format import load_conf

BATCH_SIZE = 1000


def resolve_script(batch_size, host, port, db_name, verbose=False, url_debug=False):
    db = prepare_db(host, port, db_name)
    skip = 0
    todo = count_and_log(db, batch_size, skip=skip, retry_days=0)
    while todo:
        done, skip = resolve_loop(batch_size, db, todo, skip, verbose=verbose, url_debug=url_debug, retry_days=0)
        todo = count_and_log(db, batch_size, done=done, skip=skip, retry_days=0)


if __name__ == '__main__':
    resolve_script(BATCH_SIZE, **load_conf(".")["database"])
