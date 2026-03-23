#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import qilib bo'lmadi. Virtual muhit faol va "
            "requirements o'rnatilganligini tekshiring."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
