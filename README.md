# docker-dropbox-app
Syncronization dropbox app

- AMD64 [![](https://images.microbadger.com/badges/version/rbonghi/dropbox.svg)](https://microbadger.com/images/rbonghi/dropbox "Get your own version badge on microbadger.com") [![](https://images.microbadger.com/badges/image/rbonghi/dropbox.svg)](https://microbadger.com/images/rbonghi/dropbox "Get your own image badge on microbadger.com") 
- ARM64 [![](https://images.microbadger.com/badges/version/rbonghi/dropbox:arm64-latest.svg)](https://microbadger.com/images/rbonghi/dropbox:arm64-latest "Get your own version badge on microbadger.com") [![](https://images.microbadger.com/badges/image/rbonghi/dropbox:arm64-latest.svg)](https://microbadger.com/images/rbonghi/dropbox:arm64-latest "Get your own image badge on microbadger.com") 

When your docker is ready, all files and folders will be sync in **realtime**. A watchdog check every time if a file or folder is created, deleted or modified, and will be update your dropbox folder.

If you add in your root a file `.dropboxignore` you can select witch type of file or folder you want exclude, look like your git repository.

## Start with docker
To use this docker is really easy:
1. Create your App in dropbox
2. Pull this docker
```
docker pull rbonghi/dropbox
```
3. Run your docker
```
docker run -e DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE> -v <FOLDER YOU WANT SYNC>:/dropbox dropbox
```

## Start with docker-compose
How to start up the docker-dropbox app machine:
1. Create your App in dropbox
2. Write your docker-compose.yml file or add:
```yml
version: '3'
services:
  dropbox:
    image: rbonghi/dropbox:latest
    environment:
      - PYTHONUNBUFFERED=1
      - DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE>
    volumes:
      - <FOLDER YOU WANT SYNC>:/dropbox
```
3. start your docker:
```
docker-compose up
```

# Configuration
You have two option to run the dropboxsync:
* **--fromLocal** *[default]* For each update (create, delete, modification, move) the folder in your dropbox account will be updated
* **--fromDropbox** Every 60seconds the dropbox folder will be syncronized from your dropbox account

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
    command: ["--fromDropbox"]
    environment:
      - PYTHONUNBUFFERED=1
      - DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE>
    volumes:
      - <FOLDER YOU WANT SYNC>:/dropbox
```

# Start without docker

# Make manifest for amd64 and arm
Use this manifest for multi architect version
```
docker manifest create rbonghi/dropbox:latest rbonghi/dropbox:amd64-latest rbonghi/dropbox:arm64-latest
docker manifest annotate --os linux --arch arm64 --variant armv8 rbonghi/dropbox:latest rbonghi/dropbox:arm64-latest
docker manifest push rbonghi/dropbox:latest
```

