# Adapted from Joseph Ernest https://gist.github.com/josephernest/77fdb0012b72ebdf4c9d19d6256a1119


import sys, os, time, atexit, psutil
from signal import signal, SIGTERM
from gazouilloire import run
from gazouilloire.config_format import log, create_file_handler


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile='.lock', stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        if os.path.isdir(pidfile):
            self.pidfile = os.path.join(pidfile, '.lock')
            self.path = pidfile
        else:
            self.pidfile = pidfile
            self.path = os.getcwd()

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

        # write pidfile
        pid = str(os.getpid())
        open(self.pidfile,'w+').write("%s\n" % pid)

    def onstop(self):
        self.quit()
        os.remove(self.pidfile)

    def start(self, conf):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = open(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            log.error(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        create_file_handler(self.path)
        self.daemonize()
        self.run(conf)

    def stop(self, timeout):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = open(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            log.warning(message % self.pidfile)
            return False

        # Kill the daemon process
        parent = psutil.Process(pid)
        procs = parent.children(recursive=True)
        parent.terminate()
        for p in procs:
            p.terminate()
        procs.append(parent)
        gone, alive = psutil.wait_procs(procs, timeout=timeout)
        for p in alive:
            p.kill()
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
        return True

    def restart(self, conf, timeout):
        """
        Restart the daemon
        """
        self.stop(timeout)
        self.start(conf)

    def run(self, conf):
        run.main(conf)

    def quit(self):
        """
        You should override this method when you subclass Daemon. It will be called before the process is stopped.
        """