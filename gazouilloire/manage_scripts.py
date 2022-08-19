# -*- coding: utf-8 -*-

import os
import sys
import pathlib
import shutil
from gazouilloire.config_format import log

SCRIPTS_DIR = os.path.join(pathlib.Path(__file__).parent.absolute(), 'scripts')

def list_scripts(detailed=False):
    scripts = []
    for fil in sorted(os.listdir(SCRIPTS_DIR)):
        if fil.endswith(".sh"):
            scripts.append(fil)
            if detailed:
                desc = get_script_infos(fil, short=True)
                print(" - " + fil + " :" + " " * (30 - len(fil)) + desc)
    return scripts

def get_script_infos(script, short=False):
    desc = ""
    try:
        with open(os.path.join(SCRIPTS_DIR, script)) as f:
            read = False
            for line in f.readlines():
                if not line.startswith("#"):
                    break
                line = line.strip("#\n")
                if short and not line.strip():
                    continue
                if line.strip() == "- Description:":
                    read = True
                    if short:
                        continue
                elif short and line.strip() == "- Usage:":
                    break
                if read:
                    desc += line + "\n"
    except FileNotFoundError:
        log.error("There is no script named %s" % script)
    return desc.strip("\n")

def spawn_script(script, path):
    path = pathlib.Path(path).absolute()
    if os.path.exists(os.path.join(path, script)):
        return log.error("There already is a script named %s within %s please rename it first." % (script, path))
    try:
        shutil.copy(os.path.join(SCRIPTS_DIR, script), path)
        log.info("Script %s was deployed within %s" % (script, path))
    except OSError as e:
        log.error("Could not write %s file into %s: %s (%s)" % (script, path, type(e), e))

