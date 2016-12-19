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

