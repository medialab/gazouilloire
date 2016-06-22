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

- Write down the list of desired **keywords** as json array.
  
  ```json
    "keywords": [
        "amour"
    ],
  ```
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
    ./gazouilloire/run.py
``` 

- Data is stored in your mongo, you can also export it easily with simple scripts such as those in the `bin` directory:

```bash
# To export a csv with the most useful fields:
bin/export_csv.py
# To export the whole text content of the tweets:
bin/export_all_text.py
```

