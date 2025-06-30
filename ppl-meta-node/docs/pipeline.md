# Services Architecture Placement

## Title

This is the user management service.

## Scope

This service manages users for programs.

For Docker compose about the database environment:

```
environment:
  - DATABASE_URL=postgresql://user:password@db_host/db_name
```

## Evironmental variables for the email module

```
MAIL_USERNAME=your@email.com
MAIL_PASSWORD=yourpassword
MAIL_FROM=your@email.com
MAIL_PORT=587
MAIL_SERVER=smtp.yourprovider.com
MAIL_FROM_NAME=Your App Name
```