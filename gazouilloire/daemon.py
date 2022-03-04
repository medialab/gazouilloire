# Adapted from Joseph Ernest https://gist.github.com/josephernest/77fdb0012b72ebdf4c9d19d6256a1119

import os
import sys
import atexit
import psutil
from signal import signal, SIGTERM

from gazouilloire.run import main, STOP_TIMEOUT, kill_alive_processes, \
    find_running_processes, get_pids, is_already_stopping, \
    stop as main_stop
from gazouilloire.config_format import log, create_file_handler


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, path, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = os.path.join(path, '.lock')
        self.stoplock = os.path.join(path, '.stoplock')
        self.path = path

    def write_lock_file(self):
        pid = str(os.getpid())
        open(self.pidfile,'w+').write("%s\n" % pid)

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            log.error("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as e:
            log.error("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.onstop)
        signal(SIGTERM, lambda signum, stack_frame: exit())

        self.write_lock_file()

    def onstop(self):
        self.quit()
        os.remove(self.pidfile)

    def clear_zombies(self, timeout=STOP_TIMEOUT):
        # Check for a pidfile to see if the daemon already runs
        pids = get_pids(self.pidfile, self.stoplock)

        if pids:
            # Check existing processes from the list within pids
            running_processes = find_running_processes(pids)

            # Check if a stoplock file is already present and stop if necessary or clear it if there's no running process
            if os.path.exists(self.stoplock):
                is_already_stopping(pids, self.stoplock, running_processes)

            if running_processes:
                if all(running_processes):
                    message = "Gazouilloire is already running. Type 'gazou restart' to restart the collection."
                    log.error(message)
                    sys.exit(1)
                else:
                    # If the first process is the main process, go for a standard stop.
                    p = running_processes[0]
                    if p is not None and p.name().startswith("gazou") and running_processes[0].children(recursive=True):
                        self.stop(timeout)

                    # Else, kill all remaining processes
                    else:
                        processes_to_kill = []
                        for p in running_processes:
                            if p is not None and p.name().startswith("gazou"):
                                processes_to_kill.append(p)
                                p.terminate()
                        kill_alive_processes(processes_to_kill, timeout)

    def run(self, conf, max_id=0):
        """
        Run the app in the current process (no daemon)
        """
        self.clear_zombies()
        self.write_lock_file()
        main(conf, self.path, max_id)

    def start(self, conf, max_id=0):
        """
        Start the daemon
        """
        self.clear_zombies()

        # Start the daemon
        create_file_handler(self.path)
        self.daemonize()
        main(conf, self.path, max_id)

    def stop(self, timeout):
        """
        Stop the daemon
        """
        main_stop(self.path, timeout)

    def restart(self, conf, timeout, max_id):
        """
        Restart the daemon
        """
        self.stop(timeout)
        self.start(conf, max_id)

    def quit(self):
        """
        You should override this method when you subclass Daemon. It will be called before the process is stopped.
        """
