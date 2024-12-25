# This file is part of beets.
# Copyright 2016, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Updates an MPD index whenever the library is changed.

Put something like the following in your config.yaml to configure:
    mpd:
        host: localhost
        port: 6600
        password: seekrit
"""

import os
import socket
from functools import partial

from beets import config
from beets.plugins import BeetsPlugin


# No need to introduce a dependency on an MPD library for such a
# simple use case. Here's a simple socket abstraction to make things
# easier.
class BufferedSocket:
    """Socket abstraction that allows reading by line."""

    def __init__(self, host, port, sep=b"\n"):
        if host[0] in ["/", "~"]:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(os.path.expanduser(host))
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
        self.buf = b""
        self.sep = sep

    def readline(self):
        while self.sep not in self.buf:
            data = self.sock.recv(1024)
            if not data:
                break
            self.buf += data
        if self.sep in self.buf:
            res, self.buf = self.buf.split(self.sep, 1)
            return res + self.sep
        else:
            return b""

    def send(self, data):
        self.sock.send(data)

    def close(self):
        self.sock.close()


class MPDUpdatePlugin(BeetsPlugin):
    def __init__(self):
        super().__init__()
        config["mpd"].add(
            {
                "host": os.environ.get("MPD_HOST", "localhost"),
                "port": int(os.environ.get("MPD_PORT", 6600)),
                "password": "",
                "granularupdate": False,
            }
        )
        config["mpd"]["password"].redact = True

        # For backwards compatibility, use any values from the
        # plugin-specific "mpdupdate" section.
        for key in config["mpd"].keys():
            if self.config[key].exists():
                config["mpd"][key] = self.config[key].get()

        self.register_listener("database_change", self.db_change)
        self.register_listener("album_imported", partial(self.log_event, event_type="album_imported"))

    def log_event(self, event_type: str):
        self._log.info(event_type)

    def db_change(self, lib, model):
        self._log.info(f"db_change for {model}")
        self.register_listener("cli_exit", partial(self.update, model=model))

    def update(self, lib, model=None):
        self.update_mpd(
            config["mpd"]["host"].as_str(),
            config["mpd"]["port"].get(int),
            config["mpd"]["password"].as_str(),
            model=model,
        )

    def update_mpd(self, host="localhost", port=6600, password=None, model=None):
        """Sends the "update" command to the MPD server indicated,
        possibly authenticating with a password first.
        """
        self._log.info("Updating MPD database...")

        try:
            s = BufferedSocket(host, port)
        except OSError as e:
            self._log.warning("MPD connection failed: {0}", str(e.strerror))
            return

        resp = s.readline()
        if b"OK MPD" not in resp:
            self._log.warning("MPD connection failed: {0!r}", resp)
            return

        if password:
            s.send(b'password "%s"\n' % password.encode("utf8"))
            resp = s.readline()
            if b"OK" not in resp:
                self._log.warning("Authentication failed: {0!r}", resp)
                s.send(b"close\n")
                s.close()
                return

        update_cmd = b"update\n"
        self._log.info("Updating {0!r}", model)
        if model and config["mpd"]["granularupdate"]:
            relative_path = model.path.relative_to(config['directory'])
            update_cmd = f"update {relative_path}\n".encode()

        s.send(update_cmd)
        resp = s.readline()
        if b"updating_db" not in resp:
            self._log.warning("Update failed: {0!r}", resp)

        s.send(b"close\n")
        s.close()
        self._log.info("Database updated.")
