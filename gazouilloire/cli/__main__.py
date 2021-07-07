#!/usr/bin/env python
import click
import os
from gazouilloire.__version__ import __version__
from gazouilloire.config_format import create_conf_example, load_conf, log
from gazouilloire.daemon import Daemon
from gazouilloire.run import main as main_run
from gazouilloire.resolving_script import resolve_script
from gazouilloire.exports.export_csv import export_csv, count_by_step, call_database
from gazouilloire.database.elasticmanager import ElasticManager
from elasticsearch import exceptions
from twitwi.constants import TWEET_FIELDS
import shutil
import sys

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help']
}

PRESERVE_FROM_RESET = {"tweets", "links", "logs", "piles", "search_state", "media"}

@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, message='%(version)s')
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
    conf = load_conf(path)
    daemon = Daemon(path=path)
    log.info("Tweet collection will start in daemon mode")
    daemon.start(conf)


@main.command(help="Restart collection as daemon, following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--timeout', '-t', type=int, default=15, help="Time (in seconds) before killing the process.")
def restart(path, timeout):
    conf = load_conf(path)
    daemon = Daemon(path=path)
    log.info("Restarting...")
    daemon.restart(conf, timeout)


@main.command(help="Start collection following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
def run(path):
    conf = load_conf(path)
    if os.path.exists(os.path.join(path, ".lock")):
        log.error("pidfile .lock already exists. Daemon already running?")
    elif os.path.exists(os.path.join(path, ".stoplock")):
        log.error("Please wait for the daemon to stop before running a new collection process.")
    else:
        main_run(conf)


@main.command(help="Stop collection daemon.")
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--timeout', '-t', type=int, default=15, help="Time (in seconds) before killing the process.")
def stop(path, timeout):
    daemon = Daemon(path=path)
    stopped = daemon.stop(timeout)
    if stopped:
        log.info("Collection stopped")
        conf = load_conf(path)
        db = call_database(conf)
        unresolved_urls = db.count_tweets("links_to_resolve", True)
        if unresolved_urls:
            log.info("{} tweets contain unresolved urls. Run 'gazou resolve' if you want to resolve all urls.".format(
                unresolved_urls
            ))


def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


@main.command(help="Get current status.")
@click.argument('path', type=click.Path(exists=True), default=".")
def status(path):
    conf = load_conf(path)
    running = "running" if os.path.exists(os.path.join(path, ".lock")) else "not running"
    es = ElasticManager(conf["database"]["host"], conf["database"]["port"], conf["database"]["db_name"])
    try:
        tweets = es.client.cat.indices(index=es.tweets, format="json")[0]
        links = es.client.cat.indices(index=es.links, format="json")[0]
    except exceptions.NotFoundError:
        log.error(
            "{} does not exist in Elasticsearch. Try 'gazou run' or 'gazou start' " \
            "to start the collection.".format(conf["database"]["db_name"])
        )
        return
    except exceptions.ConnectionError:
        log.error("Connection to Elasticsearch failed. Is Elasticsearch started?")
        return
    media_path = os.path.join(path, conf.get("media_directory", "media"))
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
          .format(conf["database"]["db_name"], running, tweets["docs.count"], links["docs.count"], media_count,
                  tweets["store.size"].upper(), links["store.size"].upper(), media_size))


@main.command(help="Resolve urls contained in a given Elasticsearch database. Usage: 'gazou resolve'")
@click.option('--host', default="localhost")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the"
                                                                              "current directory. Usage: gazou resolve "
                                                                              "-p /path/to/directory/")
@click.option('--port', default=9200)
@click.option('--batch-size', default=5000)
@click.option('--verbose/--silent', default=False)
@click.option('--url-debug/--url-retry', default=False)
@click.option('--db-name', help="Name of the ElasticSearch database containing the tweets. "
                                "Will take precedence over --path if also given. "
                                "Usage: gazou resolve --db-name mydb")
def resolve(host, port, path, batch_size, verbose, url_debug, db_name):
    if url_debug:
        verbose = False

    if db_name is None:
        db_name = load_conf(path)["database"]["db_name"]

    resolve_script(batch_size, host, port, db_name, verbose=verbose, url_debug=url_debug)


@main.command(help="Export tweets in csv format. Type 'gazou export' to get all collected tweets, or 'gazou export "
                   "medialab médialab' to get all tweets that contain medialab or médialab")
@click.argument('query', nargs=-1)
@click.option('--columns', '--select', '-c', '-s', help="Names of fields, separated by comma. Run gazou export "
                                                        "--list-fields to see the full list of available fields. "
                                                        "Usage: gazou export -s id,hashtags,local_time")
@click.option('--until', type=click.DateTime(), help="Export tweets published strictly before the given date, "
                                                     "in isoformat")
@click.option('--since', type=click.DateTime(), help="Export tweets published after the given date (included), "
                                                     "in isoformat")
@click.option('--output', '-o', type=click.Path(exists=False), help="File to write the tweets in. By default, "
                                                                    "'export' writes in stdout. Usage: gazou export -o "
                                                                    "my_tweet_file.csv")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the"
                                                                              "current directory. Usage: gazou export "
                                                                              "-p /path/to/directory/")
@click.option('--exclude-threads/--include-threads', default=False, help="Exclude tweets from conversations or from "
                                                                         "quotes (i.e. that do not match the keywords "
                                                                         "defined in config.json). By default, threads "
                                                                         "are included.")
@click.option('--exclude-retweets/--include-retweets', default=False, help="Exclude retweets from the exported tweets")
@click.option('--verbose/--quiet', default=True, help="Display or hide the progress bar. By default, display.")
@click.option('--export-tweets-from-file', '-f', type=click.Path(exists=True), help="Take a csv file with tweets ids "
                                                                                    "and return those tweets")
@click.option('--export-threads-from-file', '-f', type=click.Path(exists=True), help="Take a csv file with tweets ids "
                                                                                     "and return the conversations "
                                                                                     "containing those tweets")
@click.option("--list-fields", is_flag=True, help="Print the full list of available fields to export then quit.")
@click.option("--resume", "-r", is_flag=True, help="Restart the export from the last id specified in --output file")
def export(path, query, exclude_threads, exclude_retweets, verbose, export_threads_from_file, export_tweets_from_file,
           columns, list_fields, output, resume, since, until):
    if resume and not output:
        log.error("The --resume option requires to set a file name with --output")
        sys.exit(1)

    if resume and not os.path.isfile(output):
        log.error("The file {} could not be found".format(output))
        sys.exit(1)

    if list_fields:
        for field in TWEET_FIELDS:
            print(field)
    else:
        conf = load_conf(path)
        export_csv(conf, query, exclude_threads, exclude_retweets, since, until,
                   verbose, export_threads_from_file, export_tweets_from_file, columns, output, resume)

@main.command(help="Get a report about the number of tweets. Type 'gazou count' to get the number of collected tweets "
                   "or 'gazou count médialab' to get the number of tweets that contain médialab")
@click.argument('query', nargs=-1)
@click.option('--until', type=click.DateTime(), help="Count tweets published strictly before the given "
                                                                   "date, in isoformat")
@click.option('--since', type=click.DateTime(), help="Count tweets published after the given date "
                                                                   "(included), in isoformat")
@click.option('--step', type=click.Choice(['seconds', 'minutes', 'hours', 'days', 'months', 'years']))
@click.option('--output', '-o', type=click.Path(exists=False), help="File to write the report in. By default, "
                                                                    "'count' writes in stdout. Usage: gazou count -o "
                                                                    "my_count_report.csv")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the"
                                                                              "current directory. Usage: gazou count "
                                                                              "-p /path/to/directory/")
@click.option('--exclude-threads/--include-threads', default=False, help="Exclude tweets from conversations or from "
                                                                         "quotes (i.e. that do not match the keywords "
                                                                         "defined in config.json). By default, threads "
                                                                         "are included.")
@click.option('--exclude-retweets/--include-retweets', default=False, help="Exclude retweets from the counted tweets")
def count(path, query, exclude_threads, exclude_retweets, output, since, until, step):
    conf = load_conf(path)
    count_by_step(conf, query, exclude_threads, exclude_retweets, since, until, output, step)

def check_valid_reset_option(element_list):
    element_list = element_list.split(",")
    for e in element_list:
        if e not in PRESERVE_FROM_RESET:
            log.error("{} is not an existing option. Elements should be one of the following:".format(e))
            for valid in PRESERVE_FROM_RESET:
                print(valid)
            sys.exit(1)
    return element_list

@main.command(help="Delete collection: es_indices and current search state will be deleted")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the "
                                                                              "current directory. Usage: gazou reset "
                                                                              "-p /path/to/directory/")
@click.option('--preserve', '-p', help="Erase everything except these elements, separated by comma. Possible values:"
                                       "tweets,links,logs,piles,search_state,media")
@click.option('--only', '-p', help="Erase only these elements, separated by comma. Possible values:"
                                       "tweets,links,logs,piles,search_state,media")
@click.option('--yes/--no', '-y/-n', default=False, help="Skip confirmation messages")
def reset(path, yes, preserve, only):
    conf = load_conf(path)
    db_name = conf["database"]["db_name"]
    if preserve and only:
        log.error("--preserve and --only cannot be used simultaneously")
        return
    if preserve:
        preserve = set(check_valid_reset_option(preserve))
    elif only:
        only = set(check_valid_reset_option(only))
        preserve = PRESERVE_FROM_RESET - only
    else:
        preserve = {}

    if not yes:
        click.confirm("Are you sure you want to reset {}?".format(db_name), abort=True)
    es = ElasticManager(conf["database"]["host"], conf["database"]["port"], db_name)
    for index in ["tweets", "links"]:
        if index not in preserve:
            confirm_delete_index(es, db_name, index, yes)
    if "search_state" not in preserve:
        file_path = os.path.join(path, ".search_state.json")
        if os.path.isfile(file_path) \
                and (yes or click.confirm(".search_state.json will be erased, do you want to continue ?")):
            os.remove(file_path)
            log.info(".search_state.json successfully erased.")
        elif not os.path.isdir(file_path):
            log.warning(".search_state.json does not exist and could not be erased.")

    for folder in ["media", "logs", "piles"]:
        if folder not in preserve:
            if folder == "media":
                folder = conf.get("media_directory", "media")
            folder_path = os.path.join(path, folder)
            if os.path.isdir(folder_path) \
                and (yes or click.confirm("{} folder will be erased, do you want to continue ?".format(folder))):
                    shutil.rmtree(folder_path)
                    log.info("{} folder successfully erased.".format(folder))
            elif not os.path.isdir(folder_path):
                log.warning("{} folder does not exist and could not be erased.".format(folder_path))


def confirm_delete_index(es, db_name, doc_type, yes):
    if yes or click.confirm("Elasticsearch index {}_{} will be erased, do you want to continue?".format(
            db_name, doc_type)):
        if es.delete_index(doc_type):
            log.info("{}_{} successfully erased".format(db_name, doc_type))
        else:
            log.warning("{}_{} does not exist and could not be erased".format(db_name, doc_type))
