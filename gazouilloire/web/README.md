# Gazouilloire Front

New interface for Gazouilloire (Twitter 'stream + search' API grabber) powered by an Elasticsearch database, featuring data-visualization & monitoring possibilities.

## Get started

### Prerequisites

Developed in Python 2.7

Install Flask (preferably in a virtual environment - be sure to run in Python 2.7):
```bash
pip install Flask
```

Install the requirements.txt :

```bash
pip install requirements.txt
```

### How to use

#### Step 1 - Start the elasticsearch
From the root folder of your elasticsearch:
```bash
flask run
```

#### Step 2 - Start the server
From the root folder of the project, in a terminal tab you'll keep open:
```bash
flask run
```
#### Step 2 - Start the app
Still from the root folder of the project, in another tab you'll keep open too:
```bash
npm run dev
```

============
============


# Gazouilloire Web exports tool

Using the same virtualenv/dependencies as gazouilloire

## Development

```
python app.py
```

## Production

- Install mod_wsgi

Unde Debian or Ubuntu :

```bash
apt-get install libapache2-mod-wsgi
```

Or with CentOS, RedHat, Fedora... :

```bash
yum install mod_wsgi
```

- Create wsgi file

```bash
cp web.wsgi{.example,}
```

Edit the newly created `web.wsgi` and edit the path of the virtualenv having gazouilloire's dependencies, or comment these two lines if you installed dependencies globally.

- Setup Apache

Copy the example Apache config and adapt it to your local config (depending how and where you want to serve the app depending on your server config).

```bash
cp apache.conf{.example,}
```

