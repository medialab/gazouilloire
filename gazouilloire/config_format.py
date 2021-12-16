import json
import os
import sys
from shutil import copyfile
import logging
from datetime import datetime
import gzip

LOG_FORMAT = '%(asctime)s - %(processName)s [%(process)d] - %(levelname)s - %(message)s'

log = logging.getLogger("gazouilloire")
log.setLevel(logging.INFO)

# create console handler with the lowest log level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
log.addHandler(console_handler)


def create_file_handler(path):
    # create file handler for logs in daemon mode
    dir_path = os.path.join(os.path.realpath(path), "logs")
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, datetime.strftime(datetime.now(), "%Y%m%d-%H%M.log"))
    for past_file in os.listdir(dir_path):
        past_file = os.path.join(dir_path, past_file)
        if past_file != file_path and past_file.endswith(".log"):
            with open(past_file, 'rb') as src, gzip.open(past_file.replace(".log", ".log.gz"), 'wb') as dst:
                dst.writelines(src)
            os.remove(past_file)
    log.info("Tweets collection logs will print to {}".format(file_path))
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    log.addHandler(file_handler)


def load_conf(dir_path):
    real_path = os.path.realpath(dir_path)
    file_path = os.path.join(real_path, "config.json")
    if os.path.isfile(file_path):
        try:
            with open(file_path, "r") as confile:
                conf = required_format(json.load(confile))
        except Exception as e:
            log.error('Could not open %s: %s %s' % (file_path, type(e), e))
            sys.exit(1)
        conf["path"] = real_path
        return conf
    else:
        log.error('file {} does not exist. Try running the following command:\ngazouilloire init <your_path>'
                  .format(file_path))
        sys.exit(1)


def create_conf_example(dir_path):
    file_path = os.path.join(dir_path, "config.json")
    if not os.path.isfile(file_path):
        copyfile(os.path.join(os.path.dirname(__file__), "config.json.example"), file_path)
        return True
    else:
        log.warning('A file named config.json already exists in %s' % os.path.realpath(dir_path))
        return False


def required_format(conf):
    subfields = {
        "twitter": ["key", "secret", "oauth_token", "oauth_secret"],
        "database": ["host", "port", "db_name"],
        "timezone": []
    }
    for field in subfields:
        if field not in conf:
            log.error('required element %s is missing in config.json' % field)
            sys.exit(1)
        for subfield in subfields[field]:
            if subfield not in conf[field]:
                log.error('required element %s is missing in config.json' % subfield)
                sys.exit(1)
    query_terms = {'keywords': [], 'url_pieces': [], 'time_limited_keywords': {}}
    for k in query_terms:
        if k not in conf:
            conf[k] = query_terms[k]
    if all(len(conf[k]) == 0 for k in query_terms):
        log.error(
            'at least one of the query fields (keywords, url_pieces, time_limited_keywords) must be filled in '
            'in config.json '
        )
        sys.exit(1)

    if not conf["database"].get("multi_index", False) and "nb_past_months" in conf["database"] and \
            conf["database"]["nb_past_months"] > 0:
        log.error(
            'if "multi_index" is set to false or omitted in config.json, "nb_past_months" is not supported. '
            'Please set "nb_past_months" to 0 in the config file or set "multi_index" to true.'
        )
        sys.exit(1)

    if conf["database"].get("multi_index", False):
        if "nb_past_months" not in conf["database"] or conf["database"]["nb_past_months"] == 0:
            log.warning(
                '"multi_index" is set to true in config.json but "nb_past_months" is not indicated. '
                'Setting "nb_past_months" to 12.'
            )
            conf["database"]["nb_past_months"] = 12

        if conf["database"]["nb_past_months"] > 12:
            log.error(
                'When using "multi_index", "nb_past_months" is limited to 12 months max. '
                'Please set "nb_past_months" to 12 or less in the config file.'
            )
            sys.exit(1)



    if "download_media" in conf:
        for subfield in ["photos", "videos", "animated_gifs"]:
            if type(conf["download_media"][subfield]) != bool:
                log.error(
                    "The '{}' parameter in config.json should be set to either true or false".format(subfield)
                )
                sys.exit(1)

    if conf["verbose"]:
        log.setLevel(logging.DEBUG)
    return conf
