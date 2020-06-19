import gzip

source = sys.argv[1]

def gzip_open(filename):
    return gzip.open(filename, mode="rt")

open_wrapper = gzip_open if source.endswith(".gz") else open
with open_wrapper(source) as f:
    for line in f:
        sys.stdout.write(line.replace('\0', ''))
