# Processes

## User capabilities

user_logins
user_logouts


## Nginx program micro service

1. User logs in
2. Triggers a program use case
3. The program module of the program microservice handles the use case flow:
    1. Pushes progress notifications via endpoint(s)
    2. Logs the progress of the program use case
    3. Logs the dev oriented milestones
4. Each step of the progam flow is traceable:
    1. To the user that initiated it.
    2. The microservices step flow points (which is the current step out of the total steps required).

## Intro prompt on the architecture

The current project is a complete user management service developed as a headless backend in python. This project is to be a part of a micro services ecosystem where the micro services like this one exposes their functionalitites via rest apis using uvicorn over http. An orchestrator handles the use case execution flow and a nginx reverse proxy handles public traffic over https. 