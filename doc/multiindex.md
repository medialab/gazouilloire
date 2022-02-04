# Using gazouilloire in multi-index mode

If you start a collection that you think will become very large (more than 100 million tweets), 
you will probably run into disk space problems. It takes about **1GB of storage space per million** tweets collected. 
Because of this, you will probably want to compress some of the past data so you can continue to store the current stream. 

Gazouilloire provides a **multi-index mode** for this purpose: 
the data is stored month by month in separate elasticsearch indices that you can export in csv format and then 
delete as you go. You can set the time period during which an index remains **active**. 
For example, if you set this period to 1 month, Twitter will continue to update the number of likes and retweets 
received by past tweets during a month, as well as trace the conversations that happened during the past month. 
Older tweets will no longer be updated. This way, you can safely erase "inactive" indices without compromising the 
functioning of gazouilloire.

## Start the collection in multi-index mode
To start your collection in **multi-index mode**, open the `config.json` file and set `"multi_index"` to `true`.
Choose the number of past active months by changing the value of `nb_past_months`. If you leave the value at 0, 
Twitter will use 12 months as the default.

The maximum value is **12 months**.

## Check out space occupation
To find out about the size (in GB and in number of tweets) of each index, you can use the `gazou status -l` command.
You can also ask about one specific index by typing `gazou status -i 2022-02` (if you want to know the volume of 
tweets posted in February 2022). To obtain the list of **inactive** indices (and their size), type 
`gazou status -i inactive`. These indices can be safely exported in csv format, and then deleted.

## Resolve urls
Before exporting, you may want to resolve redirected urls for the inactive indices only:
```bash
gazou resolve -i inactive
```

## Export and delete indices
To export and delete inactive indices:
```bash
gazou export -i inactive
gazou close -d -i inactive
```

To export and delete specific indices (for example January and February 2022):
```bash
gazou export -i 2022-02,2022-01
gazou close -d -i 2022-02,2022-01
```

On very large indices, elasticsearch is sometimes quite slow to export data. 
Using the --step parameter can speed up the process:
```bash
 gazou export --step hours
```

