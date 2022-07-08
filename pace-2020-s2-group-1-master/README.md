# PACE 2020 S2 - EY Data and Analytics

## Overview

The goal of this project is to query datasets using Natural Language. We would like to allow individuals with no coding experience to query different datasets with ease and as little set up as possible.

To aid in portability, this template has been developed in [Docker](https://www.docker.com/). If you don't have experience with Docker already take some time to go through the offical [get started](https://docs.docker.com/get-started/) documentation. Once you have Docker installed on your machine and feel confident with **at least part 1 and 2** of the tutorial you can continue with the steps below. _Taking the time to learn Docker will be an invaluable learning experience for your career as a software developer._

## Setup

1. **Clone the Template Repo**

Clone a local copy of the repo onto your machine and `cd` into the project directory.

    $ git clone https://github.com/murphce/pace-2020-s2-group-1
    $ cd pace-2020-s2-group-1
    
When using git as a team we strongly encourage using the following methodology: [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/) _You should print the graphic on this page out and post it on your bedroom wall, analyse it once before you go to bed and again when you wake up in the morning. Everyday._

2. **Spin up the Docker Containers**

The applicaion is made up of a Flask UI and a PostgreSQL database. For ease of use, a Docker Compose file has been set up in order to build the application in one command:

    $ docker-compose up --build

    
3. **Check the App is working!**

If your installation has worked correctly you should see your Flask application is visitable at the following url http://localhost:5000. If are you having any trouble, feel free to contact [Cesar Murphy](mailto:cesar.murphy@au.ey.com).

_Impress Us_ 😉
"# EY-NLP-project" 
