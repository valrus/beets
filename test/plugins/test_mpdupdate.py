import os
import logging
import beets
import shutil
import itertools
from unittest import mock
from shlex import quote
from beets.test import _common
from beets.test.helper import PluginTestCase
from beetsplug import mpdupdate
from beetsplug.mpdupdate import BufferedSocket
from beets.util import bytestring_path, syspath

log = logging.getLogger("beets")

class MpdUpdateTestBase(PluginTestCase):
    plugin = "mpdupdate"
    preload_plugin = False

    def setUp(self):
        super().setUp()

        self.config["directory"] = self.temp_dir.decode('utf-8')

        self.ipath = os.path.join(self.temp_dir, b"testfile.mp3")
        shutil.copy(
            syspath(os.path.join(_common.RSRC, b"full.mp3")),
            syspath(self.ipath),
        )
        self.i = beets.library.Item.from_path(self.ipath)

    def tearDown(self):
        super().tearDown()
        if os.path.exists(self.ipath):
            os.remove(self.ipath)

class GranularUpdateTest(MpdUpdateTestBase):
    def setUp(self):
        super().setUp()
        self.config["mpd"]["granularupdate"] = True

        # self.setup_test()
        self.load_plugins()


    def test_item_added(self):
        log.info('{0!r}', self.i)
        with mock.patch('beetsplug.mpdupdate.BufferedSocket', autospec=True) as mocket:
            # item.store()
            instance = mocket.return_value
            instance.readline.side_effect = itertools.cycle([
                b"OK MPD",
                b"updating_db",
            ])
            self.lib.add(self.i)
            beets.plugins.send("cli_exit", lib=self.lib)
            log.info(str(instance.send.mock_calls))
            assert mock.call(f"update testfile.mp3\n".encode()) in instance.send.mock_calls
            assert False


class NonGranularUpdateTest(MpdUpdateTestBase):
    def setUp(self):
        super().setUp()

        # self.setup_test()
        self.load_plugins()

    def test_album_added(self):
        log.info('{0!r}', self.i)
        with mock.patch('beetsplug.mpdupdate.BufferedSocket', autospec=True) as mocket:
            instance = mocket.return_value
            instance.readline.side_effect = itertools.cycle([
                b"OK MPD",
                b"updating_db",
            ])
            self.lib.add(self.i)
            beets.plugins.send("cli_exit", lib=self.lib)
            log.info(str(instance.send.mock_calls))
            assert mock.call(b"update\n") in instance.send.mock_calls
