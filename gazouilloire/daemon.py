# Adapted from Joseph Ernest https://gist.github.com/josephernest/77fdb0012b72ebdf4c9d19d6256a1119

import os
import sys
import atexit
import psutil
from signal import signal, SIGTERM

from gazouilloire.run import main, STOP_TIMEOUT, kill_alive_processes, stop as main_stop
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

    def search_pid(self, timeout=STOP_TIMEOUT):
        already_stopping = os.path.isfile(self.stoplock)

        # Check for a pidfile to see if the daemon already runs
        try:
            pf = open(self.pidfile, 'r')
            pids = pf.readlines()
            pf.close()
        except IOError:
            pids = None

        if pids:
            running_processes = []
            for pid in pids:
                try:
                    p = psutil.Process(int(pid))
                    if p.status() == "zombie":
                        running_processes.append(None)
                    running_processes.append(p)
                except psutil.NoSuchProcess:
                    running_processes.append(None)

            if already_stopping and not any(running_processes):
                os.remove(self.stoplock)
                already_stopping = False

            if already_stopping:
                log.error("Gazouilloire is currently stopping. Please wait before trying to start, restart or stop.")
                sys.exit(1)

            if all(running_processes):
                message = "Gazouilloire is already running. Type 'gazou restart' to restart the collection."
                log.error(message)
                sys.exit(1)
            else:
                # If the first process is the main process, go for a standard stop.
                p = running_processes[0]
                if p is not None and p.name().startswith("gazou") and running_processes[0].children(recursive=True):
                    return main_stop(timeout)
                # Else, kill all remaining processes
                processes_to_kill = []
                for p in running_processes:
                    if p is not None and p.name().startswith("gazou"):
                        processes_to_kill.append(p)
                        p.terminate()
                kill_alive_processes(processes_to_kill, timeout)
                return True


    def run(self, conf):
        """
        Run the app in the current process (no daemon)
        """
        self.search_pid()
        self.write_lock_file()
        main(conf, self.path)

    def start(self, conf):
        """
        Start the daemon
        """
        self.search_pid()

        # Start the daemon
        create_file_handler(self.path)
        self.daemonize()
        main(conf, self.path)

    def stop(self, timeout):
        """
        Stop the daemon
        """
        if os.path.isfile(self.stoplock):
            return self.search_pid(timeout=timeout)
        return main_stop(self.path, timeout)

    def restart(self, conf, timeout):
        """
        Restart the daemon
        """
        self.stop(timeout)
        self.start(conf)

    def quit(self):
        """
        You should override this method when you subclass Daemon. It will be called before the process is stopped.
        """
