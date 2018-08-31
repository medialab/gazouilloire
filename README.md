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
        "@medialab_scpo"
    ],
    "url_pieces": [
        "medialab.sciencespo.fr/fr"
    ],
  ```

  Avoid using accented characters (Twitter will automatically return both tweets with and without accents, for instance searching "heros" will find both tweets with "heros" and "héros").

  Note that there are two possibilities to filter further:
  
  - geolocalisation mode: just add ``"geolocalisation": "Paris, France"` field to the config with the desired geographical boundaries or give in coordinates of the desired box as shown in the config example file
  - time limited keywords mode, in order to filter on specific keywords during planned time period:

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

* RICCI, Donato, COLOMBO, Gabriele, MEUNIER, Axel, et al. [Designing Digital Methods to monitor and inform Urban Policy. The case of Paris and its Urban Nature initiative](https://re.public.polimi.it/bitstream/11311/1038509/1/IPPA_Ricci-Colombo-Meunier-Brilli.pdf). In : 3rd International Conference on Public Policy (ICPP3)-Panel T10P6 Session 1 Digital Methods for Public Policy. SGP, 2017. p. 1-37.

* DOUAY, Nicolas, REYS, Aurélien, ROBIN, Sabrina. [L’usage de Twitter par les maires d’Île-de-France](https://journals.openedition.org/netcom/2089). NETCOM, 29-3/4 | 2015 : Visualisation des réseaux, de l’information et de l’espace, p. 275-296.


## Publications talking about Gazouilloire

* JULLIARD, Virginie. [#Theoriedugenre: comment débat-on du genre sur Twitter ?](https://www.cairn.info/revue-questions-de-communication-2016-2-page-135.html). Questions de communication, 2016, no 2, p. 135-157.

* BOTTINI, Thomas et JULLIARD, Virginie. [Entre informatique et sémiotique](https://www.cairn.info/revue-reseaux-2017-4-page-35.htm). Réseaux, 2017, no 4, p. 35-69.


## Credits & License

[Benjamin Ooghe-Tabanou](https://github.com/boogheta) @ [Sciences Po médialab](https://github.com/medialab)

Discover more of our projects at [médialab tools](http://tools.medialab.sciences-po.fr/).

This work is supported by [DIME-Web](http://dimeweb.dime-shs.sciences-po.fr/), part of [DIME-SHS](http://www.sciencespo.fr/dime-shs/) research equipment financed by the EQUIPEX program (ANR-10-EQPX-19-01).

Gazouilloire is a free open source software released under [GPL 3.0 license](LICENSE).

