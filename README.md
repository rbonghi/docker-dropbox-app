# docker-dropbox-app
Syncronization dropbox app

How to start up the docker-dropbox app machine:
1. Create your App in dropbox
2. Write your docker-compose.yml file or add:
```yml
version: '3'
services:
  dropbox:
    container_name: dropbox
    environment:
      - PYTHONUNBUFFERED=1
      - DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE>
    build:
      context: .
      dockerfile: Dockerfile
    image: dropbox
    volumes:
      - <FOLDER YOU WANT SYNC>:/dropbox
```
3. start your docker:
```
docker-compuse up
```
  
  
