# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/docker-dropbox-app or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import os
import fnmatch
import contextlib
import time
from datetime import datetime
import re
from threading import Thread, Event
import shutil
# Now not used
# import unicodedata
# import six
# Dropbox library
import dropbox
# Functions and decorators
from functools import wraps
# How it is work watchdog
# * https://pythonhosted.org/watchdog/quickstart.html#a-simple-example
# * https://stackoverflow.com/questions/32923451/how-to-run-an-function-when-anything-changes-in-a-dir-with-python-watchdog
# * https://stackoverflow.com/questions/46372041/seeing-multiple-events-with-python-watchdog-library-when-folders-are-created
from watchdog.observers import Observer
# Watchdog file events
from watchdog.events import PatternMatchingEventHandler
# Create logger for jplotlib
logger = logging.getLogger(__name__)
# Chunk size dimension
CHUNK_SIZE = 4 * 1024 * 1024
# Conflict files
# TODO: Improve with _CONFLICT_DATE_ #(\d+/\d+/\d+)
CONFLICT = r'_CONFLICT_'
# Ingnored pattern
IGNORE_PATTERNS = ["*.swp", "*.goutputstream*"]


def dropboxignore(func):
    """ Reload scripts functions """
    @wraps(func)
    def wrapped(self, event):
        # Check before create if match with dropboxignore
        if event.src_path == os.path.join(self.folder, self.dropboxignore):
            self.excludes = self.loadDropboxIgnore()
        return func(self, event)
    return wrapped


class UpDown(Thread, PatternMatchingEventHandler):

    def __init__(self, token, dbfolder, folder, dropboxignore=".dropboxignore", interval=0.5, overwrite=""):
        Thread.__init__(self)
        PatternMatchingEventHandler.__init__(self, ignore_patterns=IGNORE_PATTERNS)
        self.db_folder = dbfolder
        self.folder = folder
        self.dropboxignore = dropboxignore
        self.interval = interval
        self.overwrite = overwrite
        # Load dropbox library
        self.dbx = dropbox.Dropbox(token)
        # Load DropboxIgnore list
        self.excludes = self.loadDropboxIgnore()
        # Status initialization
        logger.debug(f"Dropbox folder name: {dbfolder}")
        logger.debug(f"Local directory: {folder}")

    def run(self):
        while not self.stopped.wait(self.interval):
            logger.debug("Dropbox remote sync")
            # Syncronize from Dropbox first
            self.syncFromDropbox(overwrite=True)
            # List of all files
            self.syncFromHost(overwrite=False, remove=True)
            # Syncronize from Dropbox first
            self.syncFromDropbox(overwrite=True)

    def start(self):
        overwrite_db = (self.overwrite == "dropbox")
        overwrite_host = (self.overwrite == "host")
        logger.info(f"Overwrite from Dropbox {overwrite_db}")
        logger.info(f"Overwrite from Host {overwrite_host}")
        # Syncronize from Dropbox first
        self.syncFromDropbox(overwrite=overwrite_db)
        # After syncronize from PC
        self.syncFromHost(overwrite=overwrite_host)
        # Load the observer
        self.observer = Observer()
        self.observer.schedule(self, self.folder, recursive=True)
        # Initialize stop event
        self.stopped = Event()
        super().start()
        # Start observer
        self.observer.start()

    def stop(self):
        self.stopped.set()
        self.observer.stop()
        self.observer.join()
        logger.debug("Server stopped")

    @dropboxignore
    def on_created(self, event):
        subfolder, name = self.getFolderAndFile(event.src_path)
        if not re.match(self.excludes, name):
            logger.debug(f"Created {name} in folder: \"{subfolder}\"")
            self.upload(event.src_path, subfolder, name)

    @dropboxignore
    def on_deleted(self, event):
        subfolder, name = self.getFolderAndFile(event.src_path)
        if re.search(CONFLICT, name):
            return
        logger.debug(f"Deleted {name} in folder: \"{subfolder}\"")
        self.delete(subfolder, name)

    @dropboxignore
    def on_modified(self, event):
        if not event.is_directory:
            subfolder, name = self.getFolderAndFile(event.src_path)
            if not re.match(self.excludes, name):
                logger.debug(f"Modified {name} in folder: \"{subfolder}\"")
                # Syncronization from Local to Dropbox
                self.upload(event.src_path, subfolder, name, overwrite=True)

    @dropboxignore
    def on_moved(self, event):
        if re.search(CONFLICT, event.dest_path):
            return
        if any([fnmatch.fnmatch(event.src_path, pattern) for pattern in IGNORE_PATTERNS]):
            subfolder, name = self.getFolderAndFile(event.dest_path)
            logger.debug(f"Modified {event.dest_path}")
            # Syncronization from Local to Dropbox
            self.upload(event.dest_path, subfolder, name, overwrite=True)
            return
        src_subfolder = os.path.relpath(event.src_path, self.folder)
        dest_subfolder = os.path.relpath(event.dest_path, self.folder)
        logger.debug(f"Move from {src_subfolder} to {dest_subfolder}")
        self.move(src_subfolder, dest_subfolder)

    def syncFromHost(self, overwrite=False, remove=False):
        for dn, dirs, files in os.walk(self.folder):
            # Get local folder
            subfolder = dn[len(self.folder):].strip(os.path.sep)
            # Get list from dropbox folder
            listing = self.list_folder(subfolder)
            list_files = {}
            list_folders = {}
            for k, v in listing.items():
                if isinstance(v, dropbox.files.FileMetadata):
                    list_files[k] = v
                else:
                    list_folders[k] = v
            logger.debug(f"In folder \"{subfolder}\" ...")
            # exclude dirs
            dirs[:] = [d for d in dirs if not re.match(self.excludes, d)]
            # exclude files
            files = [f for f in files if not re.match(self.excludes, f)]
            # Upload only PC files
            for name in list(set(files) - set(list_files)):
                fullname = os.path.join(dn, name)
                # TODO: Check if is required
                # if not isinstance(name, six.text_type):
                #    name = name.decode('utf-8')
                # nname = unicodedata.normalize('NFC', name)
                if re.search(CONFLICT, fullname):
                    continue
                # Remove file not in list
                if remove:
                    logger.info(f"Remove file {fullname}")
                    os.remove(fullname)
                else:
                    # Upload file
                    self.upload(fullname, subfolder, name, overwrite=overwrite)
            # Remove folders
            if remove:
                for name in list(set(dirs) - set(list_folders)):
                    fullname = os.path.join(dn, name)
                    logger.info(f"Remove folder {fullname}")
                    shutil.rmtree(fullname)

    def syncFromDropbox(self, subfolder="", overwrite=False):
        for nname, md in self.list_folder(subfolder).items():
            path = self.folder + subfolder + "/" + nname
            # Check if is a file
            if isinstance(md, dropbox.files.FileMetadata):
                res = self.download(subfolder, nname)
                # Store file in folder
                if os.path.exists(path):
                    mtime = os.path.getmtime(path)
                    mtime_dt = datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(path)
                    if(mtime_dt == md.client_modified and size == md.size):
                        logger.debug(f"{nname} is already synced [stats match]")
                    else:
                        if not overwrite:
                            # Upload new version
                            self.upload(path, subfolder, os.path.basename(path))
                            # Store conflict data
                            basename = os.path.basename(path)
                            name_file = basename.split(".")[0]
                            date = f"{mtime_dt}".replace(" ", "_").replace(":", "")
                            path = os.path.join(os.path.dirname(path), basename.replace(name_file, f"{name_file}_CONFLICT_{date}_"))
                            logger.warn(f"Rename in {path}")
                        # Store file
                        self.storefile(res, path, md.client_modified)
                else:
                    self.storefile(res, path, md.client_modified)
            # Check if data is a folder
            if isinstance(md, dropbox.files.FolderMetadata):
                logger.debug(f"Descending into {nname} ...")
                if not os.path.exists(path):
                    os.makedirs(path)
                self.syncFromDropbox(subfolder=subfolder + "/" + nname)

    def getFolderAndFile(self, src_path):
        abs_path = os.path.dirname(src_path)
        subfolder = os.path.relpath(abs_path, self.folder)
        subfolder = subfolder if subfolder != "." else ""
        name = os.path.basename(src_path)
        return subfolder, name

    def loadDropboxIgnore(self):
        """ Load Dropbox Ignore file and exlude this files from the list
        """
        excludes = r'$.'
        path = f"{self.folder}/{self.dropboxignore}"
        ignore_files = []
        if os.path.exists(path):
            with open(path, 'r') as f:
                ignore_files = f.read().splitlines()
        if ignore_files:
            # Update exclude list
            excludes = r'|'.join([fnmatch.translate(x) for x in ignore_files]) or r'$.'
            logger.warning(f"Ignore dropbox files: {ignore_files}")
        return excludes

    def list_folder(self, subfolder, recursive=False, onlyFiles=False):
        """ List a folder.

            Return a dict mapping unicode filenames to
            FileMetadata | FolderMetadata entries.
        """
        rv = {}
        path = f"/{self.db_folder}/{subfolder.replace(os.path.sep, '/')}".rstrip('/')
        try:
            with self.stopwatch('list_folder'):
                res = self.dbx.files_list_folder(path, recursive=recursive)
        except dropbox.exceptions.ApiError as err:
            logger.debug(f"Folder listing failed for {path} -- assumed empty: {err}")
            return rv
        # Load list
        for entry in res.entries:
            # List only Files otherwise list all
            if recursive:
                name = entry.path_display.lstrip("/")
            else:
                name = entry.name
            if onlyFiles:
                if isinstance(entry, dropbox.files.FileMetadata):
                    rv[name] = entry
            else:
                rv[name] = entry
        return rv

    def storefile(self, res, filename, timedb):
        """ Store and fix datetime with dropbox datetime.
        """
        out = open(filename, 'wb')
        out.write(res)
        out.close()
        # Fix time with md time
        # https://nitratine.net/blog/post/change-file-modification-time-in-python/
        modTime = time.mktime(timedb.timetuple())
        os.utime(filename, (modTime, modTime))

    def download(self, subfolder, name):
        """ Download a file.
            Return the bytes of the file, or None if it doesn't exist.
        """
        path = self.normalizePath(subfolder, name)
        with self.stopwatch('download'):
            try:
                md, res = self.dbx.files_download(path)
            except dropbox.exceptions.ApiError as err:
                logger.error(f"API error {err.user_message_text}")
                return None
            except dropbox.exceptions.HttpError as err:
                logger.error(f"HTTP error {err}")
                return None
        data = res.content
        logger.debug(f"{len(data)} bytes; md: {md}")
        return data

    def normalizePath(self, subfolder, name):
        """ Normalize folder for Dropbox syncronization.
        """
        path = f"/{self.db_folder}/{subfolder.replace(os.path.sep, '/')}/{name}"
        while '//' in path:
            path = path.replace('//', '/')
        return path

    def upload(self, fullname, subfolder, name, overwrite=False):
        """Upload a file.
            Return the request response, or None in case of error.
        """
        path = self.normalizePath(subfolder, name)
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(fullname)
        if os.path.isdir(fullname):
            try:
                res = self.dbx.files_create_folder(path)
            except dropbox.exceptions.ApiError as err:
                logger.error(f"API ERROR {err.user_message_text}")
                return None
        else:
            f = open(fullname, 'rb')
            file_size = os.path.getsize(fullname)
            if file_size <= CHUNK_SIZE:
                data = f.read()
                with self.stopwatch(f"upload {file_size} bytes"):
                    try:
                        res = self.dbx.files_upload(data, path, mode,
                                                    client_modified=datetime(*time.gmtime(mtime)[:6]),
                                                    mute=True)
                    except dropbox.exceptions.ApiError as err:
                        logger.error(f"API ERROR {err.user_message_text}")
                        return None
            else:
                upload_session_start_result = self.dbx.files_upload_session_start(f.read(CHUNK_SIZE))
                cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id, offset=f.tell())
                commit = dropbox.files.CommitInfo(path=path)
                # Upload file
                with self.stopwatch(f"upload {file_size} bytes"):
                    while f.tell() < file_size:
                        if ((file_size - f.tell()) <= CHUNK_SIZE):
                            res = self.dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                        else:
                            self.dbx.files_upload_session_append(f.read(CHUNK_SIZE), cursor.session_id, cursor.offset)
                            cursor.offset = f.tell()
            # Info data uploaded
            logger.debug(f"uploaded as {res.name.encode('utf8')}")
        return res

    def delete(self, subfolder, name):
        """ Delete a file from dropbox.
            Return True if is fully delete from dropbox
        """
        path = self.normalizePath(subfolder, name)
        with self.stopwatch('delete'):
            try:
                self.dbx.files_delete(path)
            except dropbox.exceptions.ApiError as err:
                logger.error(f"API error {err}")
                return False
        return True

    def move(self, from_path, to_path, overwrite=False):
        """ Move a file or folder from dropbox.
            Return True if is fully moved from dropbox
        """
        while '//' in from_path:
            from_path = from_path.replace('//', '/')
        while '//' in to_path:
            to_path = to_path.replace('//', '/')
        with self.stopwatch('move'):
            try:
                self.dbx.files_move("/" + from_path, "/" + to_path, allow_shared_folder=False, autorename=overwrite, allow_ownership_transfer=False)
            except dropbox.exceptions.ApiError as err:
                logger.error(f"API error {err}")
                return False
        return True

    @contextlib.contextmanager
    def stopwatch(self, message):
        """ Context manager to print how long a block of code took.
        """
        t0 = time.time()
        try:
            yield
        finally:
            t1 = time.time()
            logger.debug(f"Total elapsed time for {message}: {(t1 - t0):.3f}")
# EOF
