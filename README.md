Gazouilloire
============

Twitter stream + search API grabber handling various config options such as collecting only during specific time periods, or limiting the collection to some locations.

HowTo
-----

- Install dependencies:

```bash
    sudo apt-get install mongodb-10gen
    pip install -r requirements.txt
```

- Copy config.json.example to config.json

- Set your [Twitter API key](https://apps.twitter.com/app/) and generate the related Access Token

```json
"twitter": {
   "key": "<Consumer Key (API Key)>xxxxxxxxxxxxxxxxxxxxx",
   "secret": "<Consumer Secret (API Secret)>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
   "oauth_token": "<Access Token>xxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
   "oauth_secret": "<Access Token Secret>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}

```

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

  Some advanced filters can be used in combination with the keywords, such as `-undesiredkeyword`, `filter:links`, `-filter:media`, `-filter:retweets`, etc. See [Twitter API's documentation](https://developer.twitter.com/en/docs/tweets/search/guides/standard-operators) for more details.

  Avoid using accented characters (Twitter will automatically return both tweets with and without accents, for instance searching "heros" will find both tweets with "heros" and "héros").

  Note that there are three possibilities to filter further:

  - **language**: in order to collect only tweets written in a specific language : just add `"language": "fr"` to the config (the language should be written in [ISO 639-1 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes))
  - **geolocalisation**: just add `"geolocalisation": "Paris, France"` field to the config with the desired geographical boundaries or give in coordinates of the desired box as shown in the config example file
  - **time_limited_keywords**: in order to filter on specific keywords during planned time period:

  ```json
  "time_limited_keywords": {
        "#m6": [
            ["2014-05-01 16:00", "2014-05-08 16:05"],
            ["2014-05-08 16:00", "2014-05-08 16:05"],
            ["2014-05-15 16:00", "2014-05-08 16:05"],
            ["2014-05-22 16:00", "2014-05-08 16:05"]
        ],
        "bieber": [
            ["2014-05-08 16:00", "2014-05-08 16:05"]
        ]
    },
  ```


- Setup extra options:

  - **resolve_redirected_links**: set to `true` or `false` to enable or disable automatic resolution of all links found in tweets (t.co links are always handled, but this allows resolving also all other shorteners like bit.ly).

  - **grab_conversations**: set to `true` to activate automatic iterative collection of all tweets to which collected tweets are answering (warning: one should account for the presence of these when processing data, it often results in collecting tweets way out of the collection time period).

  - **catchup_past_week**: Twitter's free API allows to collect tweet up to 7 days in the past only which gazouilloire does by default, set this option to `false` to disable this and only collect tweets posted after the collection was started.

  - **download_medias**: set to `true` to activate automatic downloading of all medias (images and videos) posted by users within their tweets (this does not include images from social cards). Setup the `medias_directory` field in complement to setup the absolute path where Gazouilloire should store the images and videos on the machine.

  - **timezone**: adjust the timezone within which tweets timestamps should be computed. Allowed values are proposed on Gazouilloire's startup when setting up an invalid one.


- Run with:

```bash
    ./restart.sh
    # or
    ./gazouilloire/run.py
``` 

- Data is stored in your mongo, you can also export it easily with simple scripts such as those in the `bin` directory:

```bash
# To export a csv with most fields (formatted similarily to [DMI's TCAT](https://github.com/digitalmethodsinitiative/dmi-tcat)):
bin/export_csv_as_tcat.py
# To export a csv of all tweets having a specific word in their text:
bin/export_csv_as_tcat.py medialab
# To export a csv of all tweets having one of many specific words in their text:
bin/export_csv_as_tcat.py medialab digitalhumanities datajournalism '#python'
# To export a csv of all tweets matching a specific MongoDB query, for instance by user_name:
bin/export_csv_as_tcat.py "{'user_screen_name': 'medialab_ScPo'}"
# To export a csv with the most useful fields:
bin/export_csv.py
# To export the whole text content of the tweets:
bin/export_all_text.py
```

## Publications using Gazouilloire

* WARD Jeremy K, GUILLE-ESCURET Paul, ALAPETITE Clément, "[Les « antivaccins », figure de l’anti-Science](https://www.cairn.info/revue-deviance-et-societe-2019-2-page-221.htm)" (2019), in Déviance et Société, 2019/2 (Vol. 43), p. 221-251. DOI : 10.3917/ds.432.0221

* RICCI, Donato, COLOMBO, Gabriele, MEUNIER, Axel, et al. [Designing Digital Methods to monitor and inform Urban Policy. The case of Paris and its Urban Nature initiative](https://re.public.polimi.it/bitstream/11311/1038509/1/IPPA_Ricci-Colombo-Meunier-Brilli.pdf). In : 3rd International Conference on Public Policy (ICPP3)-Panel T10P6 Session 1 Digital Methods for Public Policy. SGP, 2017. p. 1-37.

* DOUAY, Nicolas, REYS, Aurélien, ROBIN, Sabrina. [L’usage de Twitter par les maires d’Île-de-France](https://journals.openedition.org/netcom/2089). NETCOM, 29-3/4 | 2015 : Visualisation des réseaux, de l’information et de l’espace, p. 275-296.

* ANTOLINOS-BASSO Diégo, PADDEU Flaminia, DOUAY Nicolas, BLANC Nathalie. [Pourquoi le débat #EuropaCity n’a pas pris sur Twitter ?](https://journals.openedition.org/reset/1070). RESET, 7 | 2018. DOI : 10.4000/reset.1070


## Publications talking about Gazouilloire

* JULLIARD, Virginie. [#Theoriedugenre: comment débat-on du genre sur Twitter ?](https://www.cairn.info/revue-questions-de-communication-2016-2-page-135.html). Questions de communication, 2016, no 2, p. 135-157.

* BOTTINI, Thomas et JULLIARD, Virginie. [Entre informatique et sémiotique](https://www.cairn.info/revue-reseaux-2017-4-page-35.htm). Réseaux, 2017, no 4, p. 35-69.


## Credits & License

[Benjamin Ooghe-Tabanou](https://github.com/boogheta) @ [Sciences Po médialab](https://github.com/medialab)

Discover more of our projects at [médialab tools](http://tools.medialab.sciences-po.fr/).

This work is supported by [DIME-Web](http://dimeweb.dime-shs.sciences-po.fr/), part of [DIME-SHS](http://www.sciencespo.fr/dime-shs/) research equipment financed by the EQUIPEX program (ANR-10-EQPX-19-01).

Gazouilloire is a free open source software released under [GPL 3.0 license](LICENSE).

