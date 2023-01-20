# docker-dropbox-app
:whale: Docker syncronization container for Dropbox using a token app 

<p align="center">
  <a href="https://hub.docker.com/r/rbonghi/dropbox"><img alt="Docker Image Size (tag)" src="https://img.shields.io/docker/image-size/rbonghi/dropbox/latest"></a>
  <a href="https://hub.docker.com/r/rbonghi/dropbox"><img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/rbonghi/dropbox" /></a>
  <a href="https://github.com/rbonghi/docker-dropbox-app/actions/workflows/build.yml"><img alt="Build" src="https://github.com/rbonghi/docker-dropbox-app/actions/workflows/build.yml/badge.svg" /></a>
  <a href="https://github.com/rbonghi/docker-dropbox-app/actions/workflows/github-code-scanning/codeql"><img alt="CodeQL" src="https://github.com/rbonghi/docker-dropbox-app/actions/workflows/github-code-scanning/codeql/badge.svg" /></a>
</p>
<p align="center">
  <a href="https://twitter.com/raffaello86"><img alt="Twitter Follow" src="https://img.shields.io/twitter/follow/raffaello86?style=social" /></a>
  <a href="https://www.instagram.com/robo.panther/"><img alt="robo.panther" src="https://img.shields.io/badge/Follow:-robo.panther-E4405F?style=social&logo=instagram" /></a>
  <a href="https://discord.gg/BFbuJNhYzS"><img alt="Join our Discord" src="https://img.shields.io/discord/1060563771048861817?color=%237289da&label=discord" /></a>
</p>

When your docker is ready, all files and folders will be sync in **realtime**. A watchdog check every time if a file or folder is created, deleted or modified, and will be update your dropbox folder.

If you add in your root a file `.dropboxignore` you can select witch type of file or folder you want exclude, look like your git repository.

## Start with docker
To use this docker is really easy:
1. Create your [App in dropbox](https://www.dropbox.com/developers/reference/getting-started#app%20console)
2. Generated refresh token by using `init_dropbox_refreshToken.sh` script. 
3. Pull this docker
```
docker pull rbonghi/dropbox
```
4. Run your docker
```
docker run \
-e DROPBOX_APP_KEY=<WRITE YOUR APPLICATION KEY HERE> \
-e DROPBOX_APP_SECRET=<WRITE YOUR APPLICATION SECRET HERE> \
-e DROPBOX_REFRESH_TOKEN=<WRITE YOUR REFRESH TOKEN HERE>  \
-v <FOLDER YOU WANT SYNC>:/dropbox rbonghi/dropbox
```

## Start with docker-compose
How to start up the docker-dropbox app machine:
1. Create your [App in dropbox](https://www.dropbox.com/developers/reference/getting-started#app%20console)
2. Generated refresh token by using `init_dropbox_refreshToken.sh` script.
3. Write your docker-compose.yml file or add:
```yml
version: '3'
services:
  dropbox:
    image: rbonghi/dropbox:latest
    environment:
      - PYTHONUNBUFFERED=1
      - DROPBOX_APP_KEY=<WRITE YOUR APPLICATION KEY HERE>
      - DROPBOX_APP_SECRET=<WRITE YOUR APPLICATION SECRET HERE>
      - DROPBOX_REFRESH_TOKEN=<WRITE YOUR REFRESH TOKEN HERE>
    volumes:
      - <FOLDER YOU WANT SYNC>:/dropbox
```
4. Start your docker:
```
docker-compose up
```

# Configuration
You have two option to run the dropboxsync:
* **--inverval** [_Default:_ 10s] Interval refresh folder from Dropbox
* **--fromLocal** Will be overwriten from your PC follder to Dropbox
* **--fromDropbox** Will be overwriten from Dropbox to your PC folder
* **--verbose** Show all debug messages

To select this option you can run the docker machine adding:
```
docker run -e DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE> -v <FOLDER YOU WANT SYNC>:/dropbox dropbox --fromDropbox
```
or
```yml
version: '3'
services:
  dropbox:
    image: rbonghi/dropbox:latest
    command: ["--fromDropbox", "-i", "120"]
    environment:
      - PYTHONUNBUFFERED=1
      - DROPBOX_APP_KEY=<WRITE YOUR APPLICATION KEY HERE>
      - DROPBOX_APP_SECRET=<WRITE YOUR APPLICATION SECRET HERE>
      - DROPBOX_REFRESH_TOKEN=<WRITE YOUR REFRESH TOKEN HERE>
    volumes:
      - <FOLDER YOU WANT SYNC>:/dropbox
```

# Start without docker
If you want launch this script without start a docker container:
```
python dbsync \ 
--rootdir <ROOT_FOLDER> \
--folder <DROPBOX_FOLDER> \
--appKey <WRITE YOUR APP KEY HERE> \
--appSecret <WRITE YOUR APP SECRET HERE> \
[options]
```
For `[options]`:
* **--verbose** Show in detail all steps for each sync
* **--fromLocal** or **--fromDropbox** Read [Configuration](#configuration)
* **--interval** [default=60s] The Interval to sync from Dropbox in **--fromDropbox** mode
* **--refreshToken** Set the refresh token retrieved and logged in the console at first launch or via the init_script. (This will avoid the manual acceptation step via a generated access code in the navigator)
