[![DOI](https://zenodo.org/badge/16621545.svg)](https://zenodo.org/badge/latestdoi/16621545)

<p align="center">
    <img src="https://github.com/medialab/gazouilloire/blob/main/doc/NOIR.png#gh-light-mode-only" alt="logo" width="260px">
    <img src="https://github.com/medialab/gazouilloire/blob/main/doc/BLANC.png#gh-dark-mode-only" alt="logo" width="260px">
</p>

A command line tool for long-term tweets collection. Gazouilloire combines two methods to collect tweets from the 
Twitter API ("search" and "filter") in order to maximize the number of collected tweets, and automatically fills the 
gaps in the collection in case of connexion errors or reboots. It handles various config options such as:
 * collecting only during [specific time periods](#--time_limited_keywords)
 * limiting the collection to some [locations](#--geolocation)
 * resolving [redirected urls](#--resolve_redirected_links)
 * downloading only certain types of [media contents](#--download_media) (only photos and no videos, for example)
 * unfolding Twitter [conversations](#--grab_conversations)
 

Python >= 3.7 compatible.

## Summary
* [Installation](#installation)
* [Quick start](#quick-start)
* [Disk space](#disk-space)
* [Export the tweets](#export-the-tweets-in-csv-format)
* [Advanced parameters](#advanced-parameters)
* [Daemon mode](#daemon-mode)
* [Reset](#reset)
* [Development](#development)
* [Troubleshooting](#troubleshooting)
* [Publications](#publications)
* [Credits & Licenses](#credits--license)


## Installation

- Install gazouilloire
    ```bash
    pip install gazouilloire
    ```

- Install [ElasticSearch](https://www.elastic.co/downloads/elasticsearch#ga-release), version 7.X (you can also use [Docker](https://www.elastic.co/guide/en/elasticsearch/reference/7.x/docker.html) for this)

- Init gazouilloire collection in a specific directory...
    ```bash
    gazou init path/to/collection/directory
    ```
- ...or in the current directory
    ```bash
    gazou init
    ```
a `config.json` file is created. Open it to configure the collection parameters.

## Quick start
- Set your [Twitter API key](https://apps.twitter.com/app/) and generate the related Access Token

    ```json
    "twitter": {
        "key": "<Consumer Key (API Key)>xxxxxxxxxxxxxxxxxxxxx",
        "secret": "<Consumer Secret (API Secret)>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "oauth_token": "<Access Token>xxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "oauth_secret": "<Access Token Secret>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }

    ```

- Set your ElasticSearch connection (host & port) within the `database` section and choose a database name that will host your corpus' index:

    ```json
    "database": {
        "host": "localhost",
        "port": 9200,
        "db_name": "medialab-tweets"
    }
    ```

Note that ElasticSearch's databases names must be lowercased and without any space or accented character.

- Write down the list of desired **keywords** and **@users** and/or the list of desired **url_pieces** as json arrays:

    ```json
    "keywords": [
        "amour",
        "\"mots successifs\"",
        "@medialab_scpo"
    ],
    "url_pieces": [
        "medialab.sciencespo.fr/fr"
    ],
    ```
  Read below the [advanced settings](#advanced-parameters) section to setup more filters and options or to get precisions on how to properly write your queries within keywords.

- Start the collection by typing the following command in your terminal:
    ```bash
    gazou run
    ```
    or, if the config file is located in another directory than the current one:
    ```bash
    gazou run path/to/collection/directory
    ```
  Read below the [daemon](#daemon-mode) section to let gazouilloire run continuously on a server and how to set up automatic restarts.


## Disk space
Before starting the collection, you should make sure that you will have enough disk space.
It takes about 1GB per million tweets collected (**without** images and other media contents).

You should also consider starting gazouilloire in [multi-index mode](doc/multiindex.md) if the collection is planed to 
exceed 100 million tweets, or simply restart your collection in a new folder and a new `db_name` 
(i.e. open another ElasticSearch index) if the current collection exceeds 150 million tweets.

As a point of comparison, here is the number of tweets sent during the whole year 2021 containing certain keywords 
(the values were obtained with the API V2 
[tweets count](https://developer.twitter.com/en/docs/twitter-api/tweets/counts/api-reference/get-tweets-counts-all)
endpoint): 

| Query                     | Number of tweets in 2021 |
|:--------------------------|:-------------------------|
| lemondefr lang:fr         | 3 million                |
| macron lang:fr            | 21 million               |
| vaccine                   | 176 million              |

## Export the tweets in CSV format
Data is stored in your ElasticSearch, which you can direcly query. But you can also export it easily in CSV format:

```bash
# Export all fields from all tweets, sorted in chronological order:
gazou export
```

### Sort tweets
By default, tweets are sorted in chronological order, using the "timestamp_utc" field.
However, you can speed-up the export by specifying that you do not need any sort order:
```bash
gazou export --sort no
```
You can also sort tweets using one or several other sorting keys:
```bash
gazou export --sort collection_time

gazou export --sort user_id,user_screen_name
```

Please note that:
- Sorting by "id" is not possible.
- Sorting by long textual fields (links, place_name, proper_links, text, url, 
user_description, user_image, user_location, user_url) is not possible.
- Sorting by other id fields such as "user_id" or "retweeted_id" will sort these fields in
alphabetical order (100, 101, 1000, 99) and not numerical.
- Sorting by plural fields (e.g. mentions, hashtags, domains) may produce unexpected results.
- Sorting by several fields may **strongly increase export time**.

### Write into a file
By default, the `export` command writes in stdout. You can also use the -o option to write into a file:
```bash
gazou export > my_tweets_file.csv
# is equivalent to
gazou export -o my_tweets_file.csv
```
Although if you interrupt the export and need to resume it to complete in multiple sequences, 
only the -o option will work with the --resume option.

### Query specific keywords

Export all tweets containing "medialab" in the `text` field:
```bash
gazou export medialab
```
The search engine is not case sensitive and it escapes # or @: `gazou export sciencespo` will export
tweets containing "@sciencespo" or "#SciencesPo". However, it **is** sensitive to accents: `gazou export medialab`
will not return tweets containing "médialab".

Use [lucene query syntax](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#query-string-syntax)
with the `--lucene` option in order to write more complex queries:

- Use AND / OR:
    ```bash
    gazou export --lucene '(medialab OR médialab) AND ("Sciences Po" OR sciencespo)'
    ```
(note that queries containg AND or OR will be considered in lucene style even if you do not use the --lucene option)
- Query other fields than the text of the tweets:
    ```bash
    gazou export --lucene user_location:paris
    ```
- Query tweets containing non-empty fields:
    ```bash
    gazou export --lucene place_country_code:*
    ```
- Query tweets containing empty fields:
    ```bash
    gazou export --lucene 'NOT retweeted_id:*'
    # (this is equivalent to:)
    gazou export --exclude-retweets
    ```
- Note that single quotes will not match exact phrases:
    ```bash
    gazou export --lucene "NewYork OR \"New York\"" #match tweets containing "New York" or "NewYork"
    gazou export --lucene "NewYork OR 'New York'" #match tweets containing "New" or "York" or "NewYork"
    ```

### Other available options:

```bash

# Get documentation for all options of gazou export (-h or --help)
gazou export -h

# By default, the export will show a progressbar, which you can disable like this:
gazou export --quiet

# Export a csv of all tweets between 2 dates or datetimes (--since is inclusive and --until exclusive):
gazou export --since 2021-03-24 --until 2021-03-25
# or
gazou export --since 2021-03-24T12:00:00 --until 2021-03-24T13:00:00

# List all available fields for each tweet:
gazou export --list-fields

# Export only a selection of fields (-c / --columns or -s / --select the xsv way):
gazou export -c id,user_screen_name,local_time,links
# or for example to export only the text of the tweets:
gazou export --select text

# Exclude tweets collected via conversations or quotes (i.e. which do not match the keywords defined in config.json)
gazou export --exclude-threads

# Exclude retweets from the export
gazou export --exclude-retweets

# Export all tweets matching a specific ElasticSearch term query, for instance by user name:
gazou export '{"user_screen_name": "medialab_ScPo"}'

# Take a csv file with an "id" column and export only the tweets whose ids are included in this file:
gazou export --export-tweets-from-file list_of_ids.csv

# You can of course combine all of these options, for instance:
gazou export medialab --since 2021-03-24 --until 2021-03-25 -c text --exclude-threads --exclude-retweets -o medialab_tweets_210324_no_threads_no_rts.csv

```

### Count collected tweets
The Gazouilloire query system is also available for the `count` command. For example, you can count the number
of tweets that are retweets:
```bash
gazou count --lucene retweeted_id:*
```
You can also use the `--step` parameter to count the number of tweets per seconds/minutes/hours/days/months/years:
```bash
gazou count medialab --step months --since 2018-01-01 --until 2022-01-01
```
The result is written in CSV format.

### Export/Import data dumps directly with ElasticSearch

In order to run and reimport backups, you can also export or import data by dialoguing directly with ElasticSearch, with some of the many tools of the ecosystem built for this.

We recommend using [elasticdump](https://github.com/elasticsearch-dump/elasticsearch-dump), which requires to install [NodeJs](https://nodejs.dev/):
```bash
# Install the package
npm install -g elasticdump
```

Then you can use it directly or via our shipped-in script [elasticdump.sh](gazouilloire/scripts/elasticdump.sh) to run simple exports/imports of your gazouilloire collection indices:
```bash
gazou scripts elasticdump.sh
# and to read its documentation:
gazou scripts --info elasticdump.sh
```


## Advanced parameters

Many advanced settings can be used to better filter the tweets collected and complete the corpus. They can all be modified within the `config.json` file.

### - keywords
  Keywords syntax follow Twitter's search engine rules. You can forge your queries by typing them within the [website's search bar](https://twitter.com/search?q=medialab&f=live). You can input a single word, or a combination of ones separated by spaces (which will query for tweets matching all of those words). You can also write complex boolean queries such as `(medialab OR (media lab)) (Sciences Po OR SciencesPo)` but note only the Search API will be used for these ones, not the Streaming API, resulting in less exhaustive results.

  Some advanced filters can be used in combination with the keywords, such as `-undesiredkeyword`, `filter:links`, `-filter:media`, `-filter:retweets`, etc. See [Twitter API's documentation](https://developer.twitter.com/en/docs/tweets/search/guides/standard-operators) for more details. Queries including these will also only run on the Search API and not the Streaming API.

  When adding a Twitter user as a keyword, such as "@medialab_ScPo", Gazouilloire will query specifically "from:medialab_Scpo OR to:medialab_ScPo OR @medialab_ScPo" so that all tweets mentionning the user will also be collected.

  Using upper or lower case characters in keywords won't change anything.

  You can leave accents in queries, as Twitter will automatically return both tweets with and without accents through the search API, for instance searching "héros" will find both tweets with "heros" and "héros". The streaming API will only return exact results but it mostly complements the search results.

  Regarding hashtags, note that querying a word without the # character will return both tweets with the regular word and tweets with the hashtag. Adding a hashtag with the # characters inside keywords will only collect tweets with the hashtag.

  Note that there are three possibilities to filter further:

### - language
In order to collect only tweets written in a specific language: just add `"language": "fr"` to the config (the language should be written in [ISO 639-1 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes))

### - geolocation 
Just add `"geolocation": "Paris, France"` field to the config with the desired geographical boundaries or give in coordinates of the desired box (for instance `[48.70908786918211, 2.1533203125, 49.00274483644453, 2.610626220703125]`)

### - time_limited_keywords 
In order to filter on specific keywords during planned time periods, for instance:

  ```json
  "time_limited_keywords": {
        "#fosdem": [
            ["2021-01-27 04:30", "2021-01-28 23:30"]
        ]
    }
  ```
### - url_pieces
  To search for specific parts of websites, one can input pieces of urls as keywords in this field. For instance:

  ```json
  "url_pieces": [
      "medialab.sciencespo.fr",
      "github.com/medialab"
  ]
  ```

### - resolve_redirected_links 
Set to `true` or `false` to enable or disable automatic resolution of all links found in tweets (t.co links are always handled, but this allows resolving also for all other shorteners such as bit.ly).

The `resolving_delay` (set to 30 by default) defines for how many days urls returning errors will be retried before leaving them as such.

### - grab_conversations
Set to `true` to activate automatic recursive retrieval within the corpus of all tweets to which collected tweets are answering (warning: one should account for the presence of these when processing data, it often results in collecting tweets which do not contain the queried keywords and/or which are way out of the collection time period).

### - catchup_past_week
Twitter's free API allows to collect tweets up to 7 days in the past, which gazouilloire does by default when starting a new corpus. Set this option to `false` to disable this and only collect tweets posted after the collection was started.

### - download_media
Configure this option to activate automatic downloading within `media_directory` of photos and/or videos posted by users within the collected tweets (this does not include images from social cards). For instance the following configuration will only collect pictures without videos or gifs:

  ```json
  "download_media": {
      "photo": true,
      "video": false,
      "animated_gif": false,
      "media_directory": "path/to/media/directory"
  }
  ```

All fields can also be set to `true` to download everything. 
`media_directory` is the folder where Gazouilloire stores the images & videos. 
It should either be an absolute path ("/home/user/gazouilloire/my_collection/my_images"), 
or a path relative to the directory where config.json is located ("my_images").

### - timezone
Adjust the timezone within which tweets timestamps should be computed. Allowed values are proposed on Gazouilloire's startup when setting up an invalid one.

### - verbose
When set to `true`, logs will be way more explicit regarding Gazouilloire's interactions with Twitter's API.


## Daemon mode
For production use and long term data collection, Gazouilloire can run as a daemon (which means that it executes in the background, and you can safely close the window within which you started it).

- Start the collection in daemon mode with:
    ```bash
    gazou start
    ```
- Stop the daemon with:
    ```bash
    gazou stop
    ```
- Restart the daemon with:
    ```bash
    gazou restart
    ```
- Access the current collection status (running/not running, nomber of collected tweets, disk usage, etc.) with
    ```bash
    gazou status
    ```

- Gazouilloire should normally restart on its own in case of temporary internet access outages but it might occasionnally fail for various reasons such as ElasticSearch having crashed for instance. In order to ensure a long term collection remains up and running without always checking it, we recommand to program automatic restarts of Gazouilloire at least once every week using cronjobs (missing tweets will be completed up to 7 days after a crash). In order to do so, a [restart.sh](gazouilloire/scripts/restart.sh) script is proposed that handles restarting ElasticSearch whenever necessary. You can install it within your corpus directory by doing:
    ```bash
    gazou scripts restart.sh
    ```
  Usecases and cronjobs examples are proposed as comments at the top of the script. You can also consult them by doing:
    ```bash
    gazou scripts --info restart.sh
    ```

- An example script [daily_mail_export.sh](gazouilloire/scripts/daily_mail_export.sh) is also proposed to perform daily tweets exports and get them by e-mail. Feel free to reuse and tailor it to your own needs the same way:
    ```bash
    gazou scripts daily_mail_export.sh
    # and to read its documentation:
    gazou scripts --info daily_mail_export.sh
    ```

- More similar practical scripts are available for diverse usecases:
    ```bash
    # You can list them all using --list or -l:
    gazou scripts --list
    # Read each script's documentation with --info or -i (for instance for "backup_corpus_ids.sh"):
    gazou scripts --info backup_corpus_ids.sh
    # And install it in the current directory with:
    gazou scripts backup_corpus_ids.sh
    # Or within a specific different directory using --path or -p:
    gazou scripts backup_corpus_ids.sh -p PATH_TO_MY_GAZOUILLOIRE_COLLECTION_DIRECTORY
    # Or even install all scripts at once using --all or -a (--path applicable as well)
    gazou scripts --all
    ```


## Reset

- Gazouilloire stores its current search state in the collection directory. This means that if you restart Gazouilloire in the same directory, it will not search again for tweets that were already collected. If you want a fresh start, you can reset the search state, as well as everything that was saved on disk, using:

    ```bash
    gazou reset
    ```

- You can also choose to delete only some elements, e.g. the tweets stored in ElasticSearch and the media files:
    ```bash
    gazou reset --only tweets,media
    ```
    Possible values for the --only argument: tweets,links,logs,piles,search_state,media


## Development

To install Gazouilloire's latest development version or to help develop it, clone the repository and install your local version using the setup.py file:

```
git clone https://github.com/medialab/gazouilloire
cd gazouilloire
python setup.py install
```

Gazouilloire's main code relies in `gazouilloire/run.py` in which the whole multiprocess architecture is orchestrated. Below is a diagram of all processes and queues.
- The `searcher` collects tweets querying [Twitter's search API v1.1](https://developer.twitter.com/en/docs/twitter-api/v1/tweets/search/api-reference/get-search-tweets) for all keywords sequentially as much as the API rates allows
- The `streamer` collects realtime tweets using [Twitter's streaming API v1.1](https://developer.twitter.com/en/docs/twitter-api/v1/tweets/filter-realtime/api-reference/post-statuses-filter) and info on deleted tweets from users explicity followed as keywords
- The `depiler` processes and reformats tweets and deleted tweets using [twitwi](https://github.com/medialab/twitwi) before indexing them into ElasticSearch. It also extracts media urls and parent tweets to feed the `downloader` and the `catchupper`
- The `downloader` requests all media urls and stores them on the filesystem (if the `download_media` option is enabled)
- The `catchupper` collects recursively via [Twitter's lookup API v1.1](https://developer.twitter.com/en/docs/twitter-api/v1/tweets/post-and-engage/api-reference/get-statuses-lookup) parent tweets of all collected tweets that are part of a thread and feeds back the `depiler` (if the `grab_conversations` option is enabled)
- The `resolver` runs multithreaded queries on all urls found as links within the collected tweets and tries to resolve them to get unshortened and harmonized urls (if the `resolve_redirected_links` option is enabled) thanks to [minet](https://github.com/medialab/minet)

All three queues are backed up on filesystem in `pile_***.json` files to be reloaded at next restart whenever Gazouilloire is shut down.

![multiprocesses](doc/multiprocessing_diagram.png)



## Troubleshooting

### ElasticSearch

- Remember to [set the heap size](https://www.elastic.co/guide/en/elasticsearch/reference/current/heap-size.html) (at 1GB by default) when moving to production. 1GB is fine for indices under 15-20 million tweets, but be sure to set a higher value for heavier corpora.

    Set these values here `/etc/elasticsearch/jvm.options` (if you use ElasticSearch as a service) or here `your_installation_folder/config/jvm.options` (if you have a custom installation folder):
    ```
    -Xms2g
    -Xmx2g
    ```
    Here the heap size is set at 2GB (set the values at `-Xms5g -Xmx5g` if you need 5GB, etc).

- If you encounter this ElasticSearch error message:
    `max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]`:

    :arrow_right:  Increase the `max_map_count` value:

    ```bash
    sudo sysctl -w vm.max_map_count=262144
    ```

    ([source](https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html))

- If you get a _ClusterBlockException_ `[SERVICE_UNAVAILABLE/1/state not recovered / initialized]` when starting ElasticSearch:

    :arrow_right:  Check the value of `gateway.recover_after_nodes` in _/etc/elasticsearch/elasticsearch.yml_:

    ```bash
    sudo [YOUR TEXT EDITOR] /etc/elasticsearch/elasticsearch.yml
    ```

    Edit the value of **`gateway.recover_after_nodes`** to match your number of nodes (usually `1` - easily checked here : *http://host:port/_nodes*).


## Publications

### Gazouilloire presentations

- Video @ FOSDEM (english): MAZOYER Béatrice, "[Gazouilloire: a command line tool for long-term tweets collection](https://archive.fosdem.org/2021/schedule/event/open_research_gazouilloire/)". Open Research Tools and Technologies devroom, FOSDEM 2021.

- Slides (french): OOGHE-TABANOU Benjamin, "[Gazouilloire : Collecter des données dans la mare de tweets](https://drive.google.com/file/d/1nvohR3wmFwA8953_w_hkYtBb4OI4OnrH/view)". Séminaire MORDEV, Laboratoire de Linguistique Formelle, Paris 2019.



### Publications using Gazouilloire

- CASTALDO Maria, VENTURINI Tommaso, FRASCA Paolo, GARGIULO Floriana, "[The Rhythms of the Night: increase in online night activity and emotional resilience during the Covid-19 lockdown](https://arxiv.org/pdf/2007.09353.pdf)"  (2020). arXiv preprint arXiv:2007.09353.

- WARD Jeremy K, GUILLE-ESCURET Paul, ALAPETITE Clément, "[Les « antivaccins », figure de l’anti-Science](https://www.cairn.info/revue-deviance-et-societe-2019-2-page-221.htm)" (2019), in Déviance et Société, 2019/2 (Vol. 43), p. 221-251. DOI: 10.3917/ds.432.0221

- RICCI, Donato, COLOMBO, Gabriele, MEUNIER, Axel, et al. [Designing Digital Methods to monitor and inform Urban Policy. The case of Paris and its Urban Nature initiative](https://re.public.polimi.it/bitstream/11311/1038509/1/IPPA_Ricci-Colombo-Meunier-Brilli.pdf). In: 3rd International Conference on Public Policy (ICPP3)-Panel T10P6 Session 1 Digital Methods for Public Policy. SGP, 2017. p. 1-37.

- DOUAY, Nicolas, REYS, Aurélien, ROBIN, Sabrina. [L’usage de Twitter par les maires d’Île-de-France](https://journals.openedition.org/netcom/2089). NETCOM, 29-3/4 | 2015 : Visualisation des réseaux, de l’information et de l’espace, p. 275-296.

- ANTOLINOS-BASSO Diégo, PADDEU Flaminia, DOUAY Nicolas, BLANC Nathalie. [Pourquoi le débat #EuropaCity n’a pas pris sur Twitter ?](https://journals.openedition.org/reset/1070). RESET, 7 | 2018. DOI : 10.4000/reset.1070


### Publications talking about Gazouilloire

- JULLIARD, Virginie. [#Theoriedugenre: comment débat-on du genre sur Twitter ?](https://www.cairn.info/revue-questions-de-communication-2016-2-page-135.html). Questions de communication, 2016, no 2, p. 135-157.

- BOTTINI, Thomas et JULLIARD, Virginie. [Entre informatique et sémiotique](https://www.cairn.info/revue-reseaux-2017-4-page-35.htm). Réseaux, 2017, no 4, p. 35-69.


## Credits & License

[Benjamin Ooghe-Tabanou](https://github.com/boogheta), [Béatrice Mazoyer](https://github.com/bmaz),
[Jules Farjas](https://github.com/farjasju) & al @ [Sciences Po médialab](https://github.com/medialab)

Read more about Gazouilloire's migration from Python2 & Mongo to Python3 & ElasticSearch in [Jules' report](https://github.com/farjasju/medialabInternshipReport).

Discover more of our projects at [médialab tools](http://tools.medialab.sciences-po.fr/).

This work has been supported by [DIME-Web](http://dimeweb.dime-shs.sciences-po.fr/), part of [DIME-SHS](http://www.sciencespo.fr/dime-shs/) research equipment financed by the EQUIPEX program (ANR-10-EQPX-19-01).

Gazouilloire is a free open source software released under [GPL 3.0 license](LICENSE).
