#!/usr/bin/env python
import click
import os
from gazouilloire.config_format import create_conf_example, load_conf, log
from gazouilloire.daemon import Daemon
from gazouilloire.run import main as main_run
from gazouilloire.resolving_script import resolve_script
from gazouilloire.exports.export_csv import export_csv
from gazouilloire.database.elasticmanager import ElasticManager
import shutil


@click.group()
def main():
    pass


@main.command(help="Initialize collection in current directory. The command creates a config.json file where the "
                   "collection parameters have to be configured before launching 'gazouilloire start'")
@click.argument('path', type=click.Path(exists=True), default=".")
def init(path):
    if create_conf_example(path):
        print(
            "Welcome to Gazouilloire! \nPlease make sure that Elasticsearch 7 is installed and edit {}"
            "\nConfiguration parameters are detailed in https://github.com/medialab/gazouilloire#howto"
            .format(os.path.join(os.path.realpath(path), "config.json")))


@main.command(help="Start collection as daemon, following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
def start(path):
    log.info("Tweet collection will start in daemon mode")
    conf = load_conf(path)
    daemon = Daemon(pidfile=path)
    daemon.start(conf)


@main.command(help="Restart collection as daemon, following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
def restart(path):
    log.info("Restarting...")
    conf = load_conf(path)
    daemon = Daemon(pidfile=path)
    daemon.restart(conf)


@main.command(help="Start collection following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
def run(path):
    conf = load_conf(path)
    if os.path.exists(os.path.join(path, ".lock")):
        log.error("pidfile .lock already exists. Daemon already running?")
    else:
        main_run(conf)


@main.command(help="Stop collection daemon.")
@click.argument('path', type=click.Path(exists=True), default=".")
def stop(path):
    daemon = Daemon(pidfile=path)
    stopped = daemon.stop()
    if stopped:
        log.info("Collection stopped")


def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


@main.command(help="Get current status.")
@click.argument('path', type=click.Path(exists=True), default=".")
def status(path):
    conf = load_conf(path)["database"]
    running = "running" if os.path.exists(os.path.join(path, ".lock")) else "not running"
    es = ElasticManager(conf["host"], conf["port"], conf["db_name"])
    tweets = es.client.cat.indices(index=es.tweets, format="json")[0]
    links = es.client.cat.indices(index=es.links, format="json")[0]
    media_path = os.path.join(path, "medias")
    media_count = 0
    media_size = 0
    if os.path.isdir(media_path):
        for (path, dirs, files) in os.walk(media_path):
            for f in files:
                media_size += os.path.getsize(os.path.join(path, f))
                media_count += 1
    media_size = sizeof_fmt(media_size)
    print("name: {}\nstatus: {}\ntweets: {}\nlinks: {}\nmedia: {}\ndisk space tweets: {}\n"
          "disk space links: {}\ndisk space media: {}"
          .format(conf["db_name"], running, tweets["docs.count"], links["docs.count"], media_count,
                  tweets["store.size"].upper(), links["store.size"].upper(), media_size))


@main.command(help="Resolve urls contained in a given Elasticsearch database. Usage: 'gazou resolve db_name'")
@click.argument('db_name', required=True, type=str)
@click.option('--host', default="localhost")
@click.option('--port', default=9200)
@click.option('--batch_size', default=5000)
@click.option('--verbose/--silent', default=False)
def resolve(host, port, db_name, batch_size, verbose):
    resolve_script(batch_size, host, port, db_name, verbose=verbose)


@main.command(help="Export tweets in csv format. Type 'gazou export' to get all collected tweets, or 'gazou export "
                   "medialab médialab' to get all tweets that contain medialab or médialab")
@click.argument('query', nargs=-1)
@click.option('--columns', '--select', '-c', '-s', help="Names of fields, separated by comma. Usage: gazou export -s "
                                                        "id,hashtags,local_time")
@click.option('--output', '-o', type=click.Path(exists=False), help="File to write the tweets in. By default, "
                                                                    "'export' writes in stdout. Usage: gazou export -o "
                                                                    "my_tweet_file.csv")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the"
                                                                              "current directory. Usage: gazou export "
                                                                              "-p /path/to/directory/")
@click.option('--exclude_threads/--include_threads', default=False, help="Exclude tweets from conversations or from "
                                                                         "quotes (i.e. that do not match the keywords "
                                                                         "defined in config.json). By default, threads "
                                                                         "are included.")
@click.option('--verbose/--quiet', default=True, help="Display or hide the progress bar. By default, display.")
@click.option('--export_threads_from_file', '-f', type=click.Path(exists=True), help="Take a csv file with tweets ids "
                                                                                     "and return the conversations "
                                                                                     "containing those tweets")
def export(path, query, exclude_threads, verbose, export_threads_from_file, columns, output):
    conf = load_conf(path)
    export_csv(conf, query, exclude_threads, verbose, export_threads_from_file, columns, output)


@main.command(help="Delete collection: es_indices and current search state will be deleted")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the "
                                                                              "current directory. Usage: gazou reset "
                                                                              "-p /path/to/directory/")
@click.option('--es_index', '-i', type=click.Choice(['none', 'tweets', 'links', 'all'], case_sensitive=False),
              default="all", help="Delete only tweet index / link index")
@click.option('--preserve_search_state/--remove_search_state', '-s', default=False, help="Preserve current search "
                                                                                         "state: gazouilloire will not "
                                                                                         "search for tweets that have "
                                                                                         "been collected in previous "
                                                                                         "runs. By default, remove "
                                                                                         "search state: "
                                                                                         "search tweets as far in the "
                                                                                         "past as possible.")
@click.option('--preserve_media/--remove_media', '-m', default=False, help="Preserve medias folder: photos, videos, "
                                                                           "etc. will not be erased. By default, "
                                                                           "erase.")
@click.option('--yes/--no', '-y/-n', default=False, help="Skip confirmation messages")
def reset(path, es_index, yes, preserve_search_state, preserve_media):
    conf = load_conf(path)["database"]
    db_name = conf["db_name"]
    if not yes:
        click.confirm("Are you sure you want to reset {}?".format(db_name), abort=True)
    es_index = es_index.lower()
    es = ElasticManager(conf["host"], conf["port"], db_name)
    if es_index == "tweets" or es_index == "all":
        confirm_delete_index(es, db_name, "tweets", yes)
    if es_index == "links" or es_index == "all":
        confirm_delete_index(es, db_name, "links", yes)
    if not preserve_search_state:
        if not yes:
            if click.confirm(".search_state.json will be erased, do you want to continue ?"):
                try:
                    os.remove(os.path.join(path, ".search_state.json"))
                    log.info(".search_state.json successfully erased.")
                except FileNotFoundError:
                    log.warning(".search_state.json does not exist and could not be erased.")
    if not preserve_media:
        if not yes:
            click.confirm("medias folder will be erased, do you want to continue ?", abort=True)
            try:
                shutil.rmtree(os.path.join(path, "medias"))
                log.info("medias folder successfully erased.")
            except FileNotFoundError:
                log.warning("medias folder does not exist and could not be erased.")


def confirm_delete_index(es, db_name, doc_type, yes):
    if yes or click.confirm("Elasticsearch index {}_{} will be erased, do you want to continue?".format(
            db_name, doc_type)):
        if es.delete_index(doc_type):
            log.info("{}_{} successfully erased".format(db_name, doc_type))
        else:
            log.warning("{}_{} does not exist and could not be erased".format(db_name, doc_type))
