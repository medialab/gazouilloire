import csv
import sys
import pytz
import click
from datetime import timedelta

def timestamp_from_tz(date, tz_name):
    return round(pytz.timezone(tz_name).localize(date).timestamp())

@click.command()
@click.argument('query')
@click.option('--start-time', type=click.DateTime(formats=['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']), required=True)
@click.option('--end-time', type=click.DateTime(formats=['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']), required=True)
@click.option('--timezone', type=click.Choice(pytz.all_timezones), default='Europe/Paris')
def make_steps(query, start_time, end_time, timezone):
    writer = csv.writer(sys.stdout)
    writer.writerow(["query"])

    until = end_time
    interval = timedelta(hours=1)

    while until > start_time:
        since = max(until - interval, start_time)
        timed_query = "{} since_time:{} until_time:{}".format(
            query,
            timestamp_from_tz(since, timezone), 
            timestamp_from_tz(until, timezone)
        )
        writer.writerow([timed_query])
        until -= interval


if __name__ == '__main__':
    make_steps()