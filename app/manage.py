#!/usr/bin/env python
"""Django management entrypoint."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.exit(__import__("django.core.management").core.management.execute_from_command_line(sys.argv))


if __name__ == "__main__":
    main()
