import json
import os
import sys
from shutil import copyfile


def load_conf(dir_path):
    file_path = os.path.join(os.path.realpath(dir_path), "config.json")
    try:
        with open(file_path, "r") as confile:
            conf = json.load(confile)
            if required_format(conf):
                for k in ['keywords', 'url_pieces', 'time_limited_keywords']:
                    if k not in conf:
                        conf[k] = []
                return conf
            else:
                print('ERROR - Some required elements are missing in %s' % file_path)
                sys.exit(1)
    except Exception as e:
        print('ERROR - Could not open %s: %s %s' % (file_path, type(e), e))
        sys.exit(1)


def create_conf_example(dir_path):
    file_path = os.path.join(dir_path, "config.json")
    if not os.path.isfile(file_path):
        copyfile(os.path.join(os.path.dirname(__file__), "config.json.example"), file_path)
    else:
        print('WARNING - A file named config.json already exists in %s' % os.path.realpath(dir_path))


def required_format(conf):
    """
    Check if config has required format
    """
    return True
