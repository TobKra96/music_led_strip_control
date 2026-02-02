# API Documentation

This directory contains the API documentation for the webserver in the form of [OpenAPI 3.1](https://swagger.io/specification/) specifications in YAML format.
The interactive documentation is generated using [Flask-OpenAPI](https://github.com/overflowdigital/Flask-OpenAPI) and is available at `/docs`.

These specifications are __only__ used for the interactive documentation and are __not__ used to validate the API requests/responses on the server side.

They also might be outdated or missing information while refactoring the API codebase.
Waiting for a stable [SwaggerUI](https://github.com/swagger-api/swagger-ui) release to make all specifications consistent.

The actual API schema and validation is located at directory `libs/webserver/schemas`.
