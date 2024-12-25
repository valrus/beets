import os
import logging
import beets
from unittest import mock
from shlex import quote
from beets.test import _common
from beets.test.helper import PluginTestCase
from beetsplug import mpdupdate
from beetsplug.mpdupdate import BufferedSocket

log = logging.getLogger("beets")

class MpdUpdateTestBase(PluginTestCase):
    plugin = "mpdupdate"
    preload_plugin = False

    def setUp(self):
        super().setUp()

        self.music_dir = os.path.expanduser(os.path.join("~", "Music"))

        i1 = _common.item()
        i1.path = beets.util.normpath(
            os.path.join(
                self.music_dir,
                "a",
                "b",
                "c.mp3",
            )
        )
        i1.title = "some item"
        i1.album = "some album"
        self.lib.add(i1)
        self.lib.add_album([i1])

        i2 = _common.item()
        i2.path = beets.util.normpath(
            os.path.join(
                self.music_dir,
                "d",
                "e",
                "f.mp3",
            )
        )
        i2.title = "another item"
        i2.album = "another album"
        self.lib.add(i2)
        self.lib.add_album([i2])

        i3 = _common.item()
        i3.path = beets.util.normpath(
            os.path.join(
                self.music_dir,
                "x",
                "y",
                "z.mp3",
            )
        )
        i3.title = "yet another item"
        i3.album = "yet another album"
        self.lib.add(i3)
        self.lib.add_album([i3])

        self.config["directory"] = self.music_dir

class GranularUpdateTest(MpdUpdateTestBase):
    def setUp(self):
        super().setUp()
        self.config["mpd"]["granularupdate"] = True

        # self.setup_test()
        self.load_plugins()


    def test_album_added(self):
        results = self.lib.items(
            "path:{}".format(
                quote(os.path.join(self.music_dir, "d", "e", "f.mp3"))
            )
        )
        item = results[0]
        log.info(f'{item}')
        with mock.patch('beetsplug.mpdupdate.BufferedSocket', autospec=True) as mocket:
            # item.store()
            instance = mocket.return_value
            instance.readline.side_effect = [
                b"OK MPD",
                b"updating_db",
            ]
            self.lib.add(item)
            self.lib.add_album([item])
            log.info(str(instance.send.mock_calls))
            relative_path = os.path.join(self.music_dir, "d", "e", "f.mp3")
            assert mock.call(f"update {relative_path}\n".encode()) in instance.send.mock_calls


class NonGranularUpdateTest(MpdUpdateTestBase):
    def setUp(self):
        super().setUp()

        # self.setup_test()
        self.load_plugins()

    def test_album_added(self):
        results = self.lib.items(
            "path:{}".format(
                quote(os.path.join(self.music_dir, "d", "e", "f.mp3"))
            )
        )
        item = results[0]
        log.info(f'{item}')
        with mock.patch('beetsplug.mpdupdate.BufferedSocket', autospec=True) as mocket:
            instance = mocket.return_value
            instance.readline.side_effect = [
                b"OK MPD",
                b"updating_db",
            ]
            beets.plugins.send("database_change", lib=self.lib, model=item)
            beets.plugins.send("cli_exit", lib=self.lib)
            log.info(str(instance.send.mock_calls))
            assert mock.call(b"update\n") in instance.send.mock_calls
