# Photo Server

A self-hosted photo library, built to replace cloud photo storage for personal use. Runs on a home Ubuntu mini PC and is accessed remotely over Tailscale.

## Features

- Drag-and-drop upload with client-side SHA-256 verification and automatic retry
- Album management: create, rename, delete, bulk move/delete, cover photo selection
- Automatic thumbnailing with EXIF-aware rotation, including HEIC/HEIF (iPhone) and RAW formats
- Sort/filter by date, name, or file type
- HTTP Basic auth, mobile-friendly responsive UI

## Stack

Python, FastAPI, Jinja2, Pillow — deployed as a systemd service.
