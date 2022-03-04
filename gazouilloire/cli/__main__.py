#!/usr/bin/env python
import click
import os
from gazouilloire.__version__ import __version__
from gazouilloire.run import STOP_TIMEOUT, find_running_processes, get_pids, stop as main_stop
from gazouilloire.config_format import create_conf_example, load_conf, log
from gazouilloire.daemon import Daemon
from gazouilloire.resolving_script import resolve_script
from gazouilloire.exports.export_csv import export_csv, count_by_step, call_database
from gazouilloire.database.elasticmanager import ElasticManager, INDEX_QUERIES
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
@click.option('--max-id', type=int, default=0, help="Search (not stream) will collect tweets from before that tweet id.")
def start(path, max_id):
    conf = load_conf(path)
    es = ElasticManager(**conf["database"])
    es.prepare_indices()
    daemon = Daemon(path=path)
    log.info("Tweet collection will start in daemon mode")
    daemon.start(conf, max_id)


@main.command(help="Restart collection as daemon, following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--max-id', type=int, default=0, help="Search (not stream) will collect tweets from before that tweet id.")
@click.option('--timeout', '-t', type=int, default=STOP_TIMEOUT, help="Time (in seconds) before killing the process.")
def restart(path, timeout, max_id):
    conf = load_conf(path)
    es = ElasticManager(**conf["database"])
    es.prepare_indices()
    daemon = Daemon(path=path)
    log.info("Restarting...")
    daemon.restart(conf, timeout, max_id)


@main.command(help="Start collection following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--max-id', type=int, default=0, help="Search (not stream) will collect tweets from before that tweet id.")
def run(path, max_id):
    conf = load_conf(path)
    daemon = Daemon(path=path)
    daemon.run(conf, max_id)


@main.command(help="Stop collection daemon.")
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--timeout', '-t', type=int, default=STOP_TIMEOUT, help="Time (in seconds) before killing the process.")
def stop(path, timeout):
    stopped = main_stop(path, timeout)
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


def print_index_status(index_name, index_info, message=None):
    print("{}{}\ntweets: {}\ndisk space tweets: {}\n".format(
        index_name if message else "name: ",
        message if message else index_name,
        index_info["docs.count"],
        sizeof_fmt(int(index_info["store.size"])).upper()
    ))


def get_bytes_index_info(es, index_name):
    return es.client.cat.indices(index=index_name, format="json", bytes="b")


@main.command(help="Get current status.")
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--index', '-i',
              help="In case of multi-index, months to consider in format YYYY-MM, or relative positions such as "
                   "'last' or first', separated by comma. Use `--index inactive` to get the status of all inactive "
                   "indices. Usage: "
                   "'gazou status -i 2018-08,2021-09' or 'gazou status -i inactive'")
@click.option('--list-indices', '-l', is_flag=True, help="print the detailed list of indices")
def status(path, index, list_indices):
    pidfile = os.path.join(path, '.lock')
    stoplock_file = os.path.join(path, '.stoplock')
    pids = get_pids(pidfile, stoplock_file)
    running_processes = find_running_processes(pids)
    if os.path.exists(stoplock_file):
        if not running_processes or not any(running_processes):
            os.remove(stoplock_file)
            running = "stopped"
        else:
            running = "stopping"
    else:
        if not running_processes:
            running = "stopped"
        elif not any(running_processes):
            os.remove(pidfile)
            running = "crashed\n" \
                      "All processes were cleared, you can safely restart."
        elif all(running_processes):
            running = "running"
        else:
            running = "unstable, restart suggested"

    conf = load_conf(path)
    es = ElasticManager(**conf["database"])
    try:
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

    print("status: {}\n".format(running))

    if es.multi_index:
        if index:
            queried_indices = es.get_valid_index_names(index, include_closed_indices=True)
            if len(queried_indices) == 1:
                index_name = queried_indices[0]
                index_info = es.client.cat.indices(index=index_name, format="json", bytes="b")[0]
                if index_info["status"] == "open":
                    print_index_status(index_name, index_info)
                else:
                    print("name: {}\nclosed\n".format(index_info["index"]))
                print("links: {}\ndisk space links: {}\n\nmedia: {}\ndisk space media: {}\n"
                      .format(links["docs.count"], links["store.size"].upper(), media_count, media_size))
                return
            if len(queried_indices) > 1:
                indices = []
                for queried in queried_indices:
                    for index in get_bytes_index_info(es, queried):
                        indices.append(index)
            else:
                log.error("There is no index corresponding to your query. Use 'gazou status -l' to list all indices")
                sys.exit(1)
        else:
            indices = get_bytes_index_info(es, es.tweets + "_*")

        summed_info = {"docs.count": 0, "store.size": 0}
        for index_info in sorted(indices, key=lambda x: x["index"]):
            if index_info["status"] == "open":
                summed_info["docs.count"] += int(index_info["docs.count"])
                summed_info["store.size"] += int(index_info["store.size"])
                if list_indices or index:
                    print_index_status(index_info["index"], index_info)
                    print("*" * 10)
            else:
                if list_indices or index:
                    print("name: {}\nclosed\n".format(index_info["index"]))
                    print("*" * 10)

        if list_indices or index:
            if indices:
                print_index_status("", summed_info, message="TOTAL")
                print("*" * 10)
            else:
                print_index_status(es.tweets, summed_info, message=" does not exist")
        else:
            print_index_status(es.tweets, summed_info)

    else:
        index_info = get_bytes_index_info(es, es.tweets)[0]
        print_index_status(es.tweets, index_info, message="")

    print("links: {}\ndisk space links: {}\n\nmedia: {}\ndisk space media: {}\n"
          .format(links["docs.count"], links["store.size"].upper(), media_count, media_size))


@main.command(help="Resolve urls contained in a given Elasticsearch database. Usage: 'gazou resolve'")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the"
                                                                              "current directory. Usage: gazou resolve "
                                                                              "-p /path/to/directory/")
@click.option('--batch-size', default=5000)
@click.option('--verbose/--silent', default=False)
@click.option('--url-debug/--url-retry', default=False)
@click.option('--host')
@click.option('--port')
@click.option('--db-name', help="Name of the ElasticSearch database containing the tweets. "
                                "Will take precedence over the config file in --path if also given. "
                                "Usage: gazou resolve --db-name mydb")
@click.option('--index', '-i',
              help="In case of multi-index, specify the index to count from. Use `--index inactive` "
                   "to count tweets from the inactive indices (i. e. not used any more for indexing). "
                   "By default, count from all opened indices.")
def resolve(path, batch_size, verbose, url_debug, host, port, db_name, index):
    if url_debug:
        verbose = False
    database_params = load_conf(path)["database"]
    if host:
        database_params["host"] = host
    if port:
        database_params["port"] = port
    if db_name:
        database_params["db_name"] = db_name
    resolve_script(**database_params, batch_size=batch_size, verbose=verbose, url_debug=url_debug, index=index)


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
@click.option('--step', type=click.Choice(['seconds', 'minutes', 'hours', 'days', 'months', 'years']),
              help="Speed up export time if you are exporting millions of tweets, by setting this option to days or "
                   "hours")
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
@click.option('--export-tweets-from-file', type=click.Path(exists=True), help="Take a csv file with tweets ids "
                                                                                    "and return those tweets")
@click.option('--export-threads-from-file', type=click.Path(exists=True), help="Take a csv file with tweets ids "
                                                                                     "and return the conversations "
                                                                                     "containing those tweets")
@click.option("--list-fields", is_flag=True, help="Print the full list of available fields to export then quit.")
@click.option("--resume", "-r", is_flag=True, help="Restart the export from the last id specified in --output file")
@click.option("--lucene", is_flag=True, help="""Use lucene query syntax.
                Usage:\n
                    gazou export --lucene "user_location:('Sao Paulo' OR Tokyo)\n"
                    gazou export --lucene "NOT(mentioned_names:*)"
                """
              )
@click.option('--index', '-i',
              help="In case of multi-index, monthly indices to export in format YYYY-MM, or relative positions such as "
                   "'last', 'first', 'inactive', separated by comma. Use `--index inactive` to export all inactive"
                   "indices (i. e. not used any more for indexing). By default, export from all opened indices.")
def export(path, query, exclude_threads, exclude_retweets, verbose, export_threads_from_file, export_tweets_from_file,
           columns, list_fields, output, resume, since, until, lucene, step, index):
    if output == "-":
        output = None
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
                   verbose, export_threads_from_file, export_tweets_from_file, columns, output, resume, lucene, step,
                   index)


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
@click.option('--index', '-i',
              help="In case of multi-index, specify the index to count from. Use `--index inactive` "
                   "to count tweets from the inactive indices (i. e. not used any more for indexing). "
                   "By default, count from all opened indices.")
@click.option("--lucene", is_flag=True, help="""Use lucene query syntax.\n
                Usage: gazou count --lucene "user_location:('Sao Paulo' OR Tokyo)"
                \ngazou count --lucene "NOT(mentioned_names:*)"
                """
              )
def count(path, query, exclude_threads, exclude_retweets, output, since, until, step, index, lucene):
    if output == "-":
        output = None
    conf = load_conf(path)
    count_by_step(conf, query, exclude_threads, exclude_retweets, since, until, output, lucene, step, index)

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
            es.delete_index(index, yes)
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
                if "download_media" in conf:
                    folder = conf["download_media"].get("media_directory", "media")
                else:
                    folder = "media"
            folder_path = os.path.join(path, folder)
            if os.path.isdir(folder_path) \
                and (yes or click.confirm("{} folder will be erased, do you want to continue ?".format(folder))):
                    shutil.rmtree(folder_path)
                    log.info("{} folder successfully erased.".format(folder))
            elif not os.path.isdir(folder_path):
                log.warning("{} folder does not exist and could not be erased.".format(folder_path))


# def confirm_delete_index(es, db_name, doc_type, yes):
#     if yes or click.confirm("Elasticsearch index {}_{} will be erased, do you want to continue?".format(
#             db_name, doc_type)):
#         es.delete_index(doc_type)


@main.command(help="Close/delete indices")
@click.option('--index', '-i', help="Months to close in format YYYY-MM, or relative positions such as 'last' or first',"
                                    "separated by comma. Use `--index inactive` to close all inactive indices. "
                                    "Run gazou status -l to see the list of existing indices. "
                                    "Usage: 'gazou close -i 2018-08,2021-09' "
                                    "or 'gazou close -i inactive'")
@click.option('--delete/--close', '-d/-c', default=False, help="Delete indices instead of closing them.")
@click.option('--force/--', '-f/-', default=False, help="Force the closure/deletion even if some indices are newer "
                                                        "than the 'nb_past_months' limit")
@click.option('--path', '-p', type=click.Path(exists=True), default=".", help="Directory were the config.json file can "
                                                                              "be found. By default, looks in the "
                                                                              "current directory. Usage: gazou reset "
                                                                              "-p /path/to/directory/")
def close(path, delete, force, index):
    conf = load_conf(path)
    es = ElasticManager(**conf["database"])

    if es.multi_index:
        if index is None:
            indices = [i for i in es.client.indices.get(es.tweets + "_*", expand_wildcards="all")]
        else:
            indices = es.get_valid_index_names(index, include_closed_indices=delete)

    else:
        if index is None:
            if force:
                indices = es.tweets
            else:
                log.error("{} is currently the only index since multi-index is not activated. Use --force option if "
                          "you want to {} this index anyway.".format(es.tweets, "delete" if delete else "close"))
                sys.exit(1)
        else:
            log.error("multi-index is not set in config.json, there should be no --index/-i parameter")
            sys.exit(1)

    es.close_indices(indices, delete, force)
