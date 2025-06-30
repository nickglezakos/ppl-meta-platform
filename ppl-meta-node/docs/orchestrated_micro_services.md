# Orchestrated Micro Services

## Concept

Automonous software projects (apps) orchestrated under a certain scope domain.

## Logic

The Orchestrated Micro Services architecture paradigm follow tha same OOP architecture archetypes at any level of architecture hierarchy. In this sense, any entity at any level (Program, Service, Function, Data)  is organised following the OOP class archetype with specific pre-conditions, post-conditions, inputs, outputs, data structures, methods and metadata.

## Orchestration

## Local microservices

uvicorn src.main:app --host 0.0.0.0 --port 8000
0.0.0.0 ----> avaiable on all network interfaces

uvicorn src.main:app --host 127.0.0.1 --port 8000
127.0.0.1 ----> available on localhost

--port 8000 can be changed

## NginX

# Nginx config directory

Directory in the server that runs nginx:
/etc/nginx/

# Config file

For a single site, edit /etc/nginx/nginx.conf or
For multiple sites, create or edit a file in /etc/nginx/sites-available/ (e.g., /etc/nginx/sites-available/yourdomain.com).

Code to be added in the config file:

server {
    listen 80;
    server_name yourdomain.com;  # or localhost for local dev

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name localhost;

    location /users/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /orders/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}


server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Enabling site

Enable the site (if using sites-available/sites-enabled):

sudo ln -s /etc/nginx/sites-available/yourdomain.com /etc/nginx/sites-enabled/

# Testing configuration

sudo nginx -t

# Reload or restart nginx

sudo systemctl reload nginx

or

sudo service nginx reload

# Nginx local installation

Install Nginx: 
brew install nginx

edit:  
/usr/local/etc/nginx/nginx.conf
use the server code above

Start Nginx:
sudo nginx

Run a microservice:
uvicorn src.main:app --host 127.0.0.1 --port 8000

Check:
http://localhost/ or curl http://localhost/your-endpoint

# Issues

# Path rewriting

A request to http://localhost/users/profile will be proxied to http://127.0.0.1:8000/users/profile.
If your FastAPI app expects endpoints like /profile (not /users/profile), this will result in a 404 error.

For a FastAPI app with routers with prefixes (e.g., app.include_router(users_router, prefix="/users")), keep the prefix in the path.

proxy_pass http://127.0.0.1:8000/; (with slash): keeps the users prefix.
proxy_pass http://127.0.0.1:8000; (no slash): strips the users prefix.

# Media files

## Structure

Nginx Configuration to serve media files:

location /media/ {
    alias /srv/media/;
}

Requests to http://yourdomain.com/media/filename.jpg will serve /srv/media/filename.jpg directly.

Docker: mount the media directory as a volume

## Network Shared File

# Installation

Ubuntu/Debian:
sudo apt-get update
sudo apt-get install nfs-kernel-server

macOS:
NFS server is built-in, but you may need to enable and configure it.
to share /srv/media:
sudo mkdir -p /srv/media
sudo chown $(whoami):staff /srv/media

2. Edit the NFS Exports File
Open /etc/exports with a text editor (you may need sudo):

sudo nano /etc/exports

Add a line like this to export the directory to your network (replace 192.168.1.0/24 with your local network or use -alldirs -mapall=$(id -u):$(id -g) for all users):
/srv/media -alldirs -mapall=501:20 192.168.1.0/24

501:20 are the default user:group IDs for the first user on macOS (check yours with id).
You can use -network 192.168.1.0 -mask 255.255.255.0 for more control.

3. Start the NFS Server
On macOS, NFS is built-in. Start (or restart) the NFS daemon:

sudo nfsd restart

4. Allow NFS Through the Firewall (if enabled)
Go to System Preferences > Security & Privacy > Firewall > Firewall Options and allow sharing, or use:

sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

5. Verify the Export
Check your exports:

showmount -e

You should see /srv/media listed.

2. If the machine is an NFS client (mounts the share):
You need to install the NFS client package.

Ubuntu/Debian:
sudo apt-get update
sudo apt-get install nfs-common

3. On your Nginx machine:
If you want Nginx to serve files from an NFS share, your Nginx machine must be an NFS client and mount the NFS directory.
If your Nginx machine is also the NFS server, install the NFS server package and export the directory.

Mounting NFS on a Microservice Host

# /etc/exports
/srv/media  *(rw,sync,no_subtree_check)

sudo exportfs -ra

On each microservice host:

sudo mount nfs-server-ip:/srv/media /srv/media




### Programs

Programs exist at the supervisory level. Programs, like services, are also organised as classes. A Program covers at least one specific use case and it governs at least one micro service. From the User point of view, a Program is a clearly defined software application that carries out at least one specific task.

### Micro services

Micro serivces are automonous software projects (apps) orchestrated by Programs under a certain scope domain. For reference and style purposes, there are two types of micro services:

- The orchestration micro service that cooridnates other micro services at the supervision level, and

- The functional micro services that carry out at least one specific task.

## OMS protocol

### Orchestrator

### Media Processor & Storage

Media class/model
    ppl-meta/media_processor.py/
    class Media:
    - with embedded take information (the MediaUserAction ?)
    - with media files per media type in different directories (.mp4, webm, etc.)
    - with sound file per video
    - with method to distinguish media types: frames/video, sound, pictures (sound to video and sound only, pictures only)
    - video (cover and) snapshots
    - Filters: XX, XX, XX

Face class/model
    - OriginMediaUID
    - OriginModelUID
    - faceRect

Body class/model
    - OriginMediaUID
    - OriginModelUID
    - bodyRect

Sound class/model
    - OriginMediaUID
    - OriginModelUID
    - XX

Storage class/model
    - media objects
    - fileTypes: number, size
    - directories: video, pictures, sound
    - deviceName
    - deviceUID

FeatureProcessor
    - deviceName
    - deviceUID

MediaUserAction class/model
    - MediumUID: Media/Storage
    - UserUID
    - Start
    - Stop
    - UserAction:
        RecordFrom, StoreTo, DeleteFrom, StoreTo, encode, applyXXFilter, duplicate, archive, delete, applyFaceFeature, applyBodyFeature, applySoundFeature


### Micro Service Class Structure

| Micro Service | |
| --- | --- |
| type | |
| name | |
| uid | |
| url | |
| scope statement| |
| logic | |
| pre conditions | |
| post conditions | |
| methods | |
| metadata | |
| | |

### Discovery processes

1. A program type micro service should interoperate with the functional type micro service(s) needed to carry out the task(s) of the use case(s).
2. The logic of fms coordination should be in the logic of the pms and subsequently should be depicted in the pre/post conditions and methods.
3. Each micro service owns a uid and a distinct url in the ecosystem. Both are used for interoperability with the other microservices.
    1. The name, uid and url of any microservice is issued by the same microservice.
    2. The name, uid and url of any microservice should be exposed via an endpoint for back-end pms and fps (a identification endpoint).
    3. The identification endpoint should be discoverabale by any pms via a standarized manner.
4. Each microservice is a standalone functional python application and it can be a back-end or a front-end.
5. Each microservice has its own database.
6. User management happens on the pms level.
7. A fps is discoverable from a pms via its uid correlation to the pms.
8. Users subscribe to an fps based on the user management logic of the pms.


## File structure of a Python micro service

| Root | Level 1 | Level 2 |
| :--------: | :--------: | :--------: |
|  | main.py | |
|  | config.py | |
|  | database.py | |
|  | logger.py | |
| venv | venv files | |
| src | | |
|  | api | |
|  |  | __init__.py|
|  |  | `service1.py`|
|  |  | `service2.py`|
|  |  | `...`|
|  | models | |
|  |  | __init__.py|
|  |  | `service1.py`|
|  |  | `service2.py`|
|  |  | `...`|
|  | schemas | |
|  |  | __init__.py|
|  |  | `service1.py`|
|  |  | `service2.py`|
|  |  | `...`|
|  | services | |
|  |  | __init__.py|
|  |  | `service1.py`|
|  |  | `service2.py`|
|  |  | `...`|
|  | logs | |
| venv | venv files | |
| venv | venv files | |
| README.md | text | text|
| requirements.txt | text | text|
| requirements.in | text | text|