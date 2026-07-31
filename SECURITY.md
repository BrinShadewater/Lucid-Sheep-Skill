# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Use GitHub's private vulnerability reporting on this repository
(**Security → Report a vulnerability**), which opens a private channel with the maintainer.

Please include what you found, how to reproduce it, and what an attacker could achieve.

## Scope

This project is a protocol and a set of instructions rather than a running service.
Reports about the protocol leaking information it promises to keep private, or about
the tooling in `starter-kit/` mishandling repository contents, are in scope.

## What this project does not do

- It does not collect telemetry, and it does not phone home.
- It does not require credentials to run its core functionality.

Please do not paste secrets, tokens, or credentials into an issue or a pull request. If you
believe you have exposed one while using this tool, rotate it first and report second.
