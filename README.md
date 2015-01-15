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

- Set your Twitter API keys inside and the list of keywords desired

- Run with:

```bash
    ./gazouilloire/run.py
``` 

- Data is stored in your mongo
