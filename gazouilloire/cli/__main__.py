#!/usr/bin/env python
import click
from gazouilloire.config_format import create_conf_example, load_conf
from gazouilloire import run
from gazouilloire.resolving_script import resolve_script
from gazouilloire.exports.export_csv import export_csv


@click.group()
def main():
    pass


@main.command(help="Initialize collection in current directory. The command creates a config.json file where the "
                   "collection parameters have to be configured before launching 'gazouilloire start'")
@click.argument('path', type=click.Path(exists=True), default=".")
def init(path):
    create_conf_example(path)


@main.command(help="Start collection following the parameters defined in config.json.")
@click.argument('path', type=click.Path(exists=True), default=".")
def start(path):
    conf = load_conf(path)
    run.main(conf)


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