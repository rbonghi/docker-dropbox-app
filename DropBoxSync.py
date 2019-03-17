"""Syncronization system for APP Dropbox.

Starting point from [1] Use API v2.

[1] https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py
"""

from __future__ import print_function

import argparse
import contextlib
import os, sys, time, logging, datetime
import fnmatch, re
import threading
import six, unicodedata
# How it is work watchdog
# * https://pythonhosted.org/watchdog/quickstart.html#a-simple-example
# * https://stackoverflow.com/questions/32923451/how-to-run-an-function-when-anything-changes-in-a-dir-with-python-watchdog
# * https://stackoverflow.com/questions/46372041/seeing-multiple-events-with-python-watchdog-library-when-folders-are-created
from watchdog.observers import Observer
#from watchdog.events import LoggingEventHandler
from watchdog.events import PatternMatchingEventHandler
# Colored terminal - https://pypi.org/project/termcolor/
from termcolor import colored, cprint
# Functions and decorators
from functools import wraps

if sys.version.startswith('2'):
    input = raw_input  # noqa: E501,F821; pylint: disable=redefined-builtin,undefined-variable,useless-suppression

import dropbox

# OAuth2 access token.
TOKEN = os.environ['DROPBOX_TOKEN'] if "DROPBOX_TOKEN" in os.environ else ""
FOLDER = os.environ['DROPBOX_FOLDER'] if "DROPBOX_FOLDER" in os.environ else "Downloads"
ROOTDIR = os.environ['DROPBOX_ROOTDIR'] if "DROPBOX_ROOTDIR" in os.environ else "~/Downloads"
INTERVAL = int(os.environ['DROPBOX_INTERVAL']) if "DROPBOX_INTERVAL" in os.environ else 60

def do_every(interval, worker_func, iterations = 0):
    """ Repeat an action in thread.
        Follow https://stackoverflow.com/questions/11488877/periodically-execute-function-in-thread-in-real-time-every-n-seconds
    """
    if iterations != 1:
        threading.Timer(
            interval,
            do_every, [interval, worker_func, 0 if iterations == 0 else iterations-1]
        ).start ()
    # Run function
    worker_func ()

def check_dropboxignore(func):
    """ Reload scripts functions """
    @wraps(func)
    def wrapped(self, event):
        # Check before create if match with dropboxignore
        if event.src_path == self.rootdir + "/" + self.dropboxignore:
            self.loadDropboxIgnore()
        return func(self, event)
    return wrapped

class UpDown(PatternMatchingEventHandler):

    def __init__(self, token, folder, rootdir, dropboxignore=".dropboxignore", verbose=False):
        super(UpDown, self).__init__(ignore_patterns=["*.swp"])
        self.folder = folder
        self.rootdir = rootdir
        self.verbose = verbose
        self.dropboxignore = dropboxignore
        if verbose:
            print('Dropbox folder name:', folder)
            print('Local directory:', rootdir)
        self.dbx = dropbox.Dropbox(token)
        # Load DropboxIgnore list
        self.loadDropboxIgnore()
        
    def loadDropboxIgnore(self):
        path = self.rootdir + "/" + self.dropboxignore
        if os.path.exists(path):
            with open(path, 'r') as f:
                ignore_files = f.read().splitlines()
        else:
            ignore_files = []
        # Upda exclude list
        self.excludes = r'|'.join([fnmatch.translate(x) for x in ignore_files]) or r'$.'
        #if self.verbose: 
        print("Update excludes:", ignore_files)
        
    def syncFromDropbox(self, subfolder=""):
        """ Recursive function to download all files from dropbox
        """
        listing = self.list_folder(subfolder)

        # Remove all folder listed
        for name in list(set(os.listdir(self.rootdir + subfolder))-set(listing.keys())):
            self.delete(subfolder, name)
        for nname in listing:
            md = listing[nname]
            path = self.rootdir + subfolder + "/" + nname
            if (isinstance(md, dropbox.files.FileMetadata)):
                res = self.download(subfolder, nname)
                # Store file in folder
                if os.path.exists(path):
                    mtime = os.path.getmtime(path)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(path)
                    if(mtime_dt == md.client_modified and size == md.size):
                        print(nname, 'is already synced [stats match]')
                    else:
                        self.storefile(res, path, md.client_modified)
                else:
                    self.storefile(res, path, md.client_modified)
            if (isinstance(md, dropbox.files.FolderMetadata)):
                if self.verbose: print('Descending into', nname, '...')
                if not os.path.exists(path):
                    os.makedirs(path)
                self.syncFromDropbox(subfolder=subfolder + "/" + nname)

    def syncFromLocal(self):

        for dn, dirs, files in os.walk(self.rootdir):
            subfolder = dn[len(self.rootdir):].strip(os.path.sep)
            listing = self.list_folder(subfolder)
            if self.verbose: print('Descending into', subfolder, '...')

            # exclude dirs
            dirs[:] = [os.path.join(subfolder, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.match(self.excludes, d)]
            # exclude files
            files = [os.path.join(subfolder, f) for f in files]
            files = [f for f in files if not re.match(self.excludes, f)]

            # First do all the files.
            for name in files:
                fullname = os.path.join(dn, name)
                if not isinstance(name, six.text_type):
                    name = name.decode('utf-8')
                nname = unicodedata.normalize('NFC', name)
                if nname in listing:
                    md = listing[nname]
                    mtime = os.path.getmtime(fullname)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(fullname)
                    if (isinstance(md, dropbox.files.FileMetadata) and
                            mtime_dt == md.client_modified and size == md.size):
                        print(name, 'is already synced [stats match]')
                    else:
                        print(name, 'exists with different stats, downloading')
                        res = self.download(subfolder, name)
                        with open(fullname) as f:
                            data = f.read()
                        if res == data:
                            print(name, 'is already synced [content match]')
                        else:
                            print(name, 'has changed since last sync')
                            # Overwrite old files
                            self.upload(fullname, subfolder, name, overwrite=True)
                # Upload all new files
                self.upload(fullname, subfolder, name)

    def getFolderAndFile(self, src_path):
        abs_path = os.path.dirname(src_path)
        subfolder = os.path.relpath(abs_path, self.rootdir)
        subfolder = subfolder if subfolder != "." else "" 
        name = os.path.basename(src_path)
        return subfolder, name
        
    def on_moved(self, event):
        subfolder, src_name = self.getFolderAndFile(event.src_path)
        _, dest_name = self.getFolderAndFile(event.dest_path)
        print("Moved", src_name, "->", dest_name, "in folder: \"{}\"".format(subfolder))
        self.move(subfolder, src_name, dest_name)
    
    @check_dropboxignore
    def on_created(self, event):
        subfolder, name = self.getFolderAndFile(event.src_path)
        if not re.match(self.excludes, name):
            print("Created", name, "in folder: \"{}\"".format(subfolder))
            self.upload(event.src_path, subfolder, name)
        
    @check_dropboxignore
    def on_deleted(self, event):
        subfolder, name = self.getFolderAndFile(event.src_path)
        print("Deleted", name, "in folder: \"{}\"".format(subfolder))
        self.delete(subfolder, name)
        
    @check_dropboxignore
    def on_modified(self, event):
        if not event.is_directory:
            subfolder, name = self.getFolderAndFile(event.src_path)
            if not re.match(self.excludes, name):
                print("Modified", name, "in folder: \"{}\"".format(subfolder))
                # Syncronization from Local to Dropbox
                self.upload(event.src_path, subfolder, name, overwrite=True)

    def list_folder(self, subfolder, recursive=False):
        """List a folder.

        Return a dict mapping unicode filenames to
        FileMetadata|FolderMetadata entries.
        """
        path = '/%s/%s' % (self.folder, subfolder.replace(os.path.sep, '/'))
        while '//' in path:
            path = path.replace('//', '/')
        path = path.rstrip('/')
        try:
            with self.stopwatch('list_folder'):
                res = self.dbx.files_list_folder(path, recursive=recursive)
        except dropbox.exceptions.ApiError as err:
            if self.verbose: print('Folder listing failed for', path, '-- assumed empty:', err)
            return {}
        else:
            rv = {}
            for entry in res.entries:
                rv[entry.name] = entry
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

    def move(self, subfolder, src_name, dest_name):
        """ Move file or folder from dropbox.
        Return True if is moved from dropbox
        """
        src_path = self.normalizePath(subfolder, src_name)
        dest_path = self.normalizePath(subfolder, dest_name)
        with self.stopwatch('delete'):
            try:
                md = self.dbx.files_move(src_path, dest_path)
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return False
        return True
    
    def delete(self, subfolder, name):
        """ Delete a file from dropbox.
        Return True if is fully delete from dropbox
        """
        path = self.normalizePath(subfolder, name)
        with self.stopwatch('delete'):
            try:
                md = self.dbx.files_delete(path)
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return False
        return True

    def download(self, subfolder, name):
        """Download a file.
        Return the bytes of the file, or None if it doesn't exist.
        """
        path = self.normalizePath(subfolder, name)
        with self.stopwatch('download'):
            try:
                md, res = self.dbx.files_download(path)
            except dropbox.exceptions.HttpError as err:
                print('*** HTTP error', err)
                return None
        data = res.content
        if self.verbose: print(len(data), 'bytes; md:', md)
        return data

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
            res = self.dbx.files_create_folder(path)
        else:
            with open(fullname, 'rb') as f:
                data = f.read()
            with self.stopwatch('upload %d bytes' % len(data)):
                try:
                    res = self.dbx.files_upload(
                        data, path, mode,
                        client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                        mute=True)
                except dropbox.exceptions.ApiError as err:
                    print('*** API error', err)
                    return None
            if self.verbose: print('uploaded as', res.name.encode('utf8'))
        return res

    def normalizePath(self, subfolder, name):
        """ Normalize folder for Dropbox syncronization.
        """
        path = '/%s/%s/%s' % (self.folder, subfolder.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        return path

    @contextlib.contextmanager
    def stopwatch(self, message):
        """Context manager to print how long a block of code took."""
        t0 = time.time()
        try:
            yield
        finally:
            t1 = time.time()
            if self.verbose: print('Total elapsed time for %s: %.3f' % (message, t1 - t0))

if __name__ == '__main__':
    """Main program.

    Parse command line, then iterate over files and directories under
    rootdir and upload all files.  Skips some temporary files and
    directories, and avoids duplicate uploads by comparing size and
    mtime with the server.
    """
    #logging.basicConfig(level=logging.INFO,
    #                    format='%(asctime)s - %(message)s',
    #                    datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(description='Sync ~/dropbox to Dropbox')
    parser.add_argument('folder', nargs='?', default=FOLDER,
                        help='Folder name in your Dropbox')
    parser.add_argument('rootdir', nargs='?', default=ROOTDIR,
                        help='Local directory to upload')
    parser.add_argument('--token', default=TOKEN,
                        help='Access token '
                        '(see https://www.dropbox.com/developers/apps)')
    parser.add_argument('--interval', default=INTERVAL,
                        help='Interval to sync from dropbox')
    parser.add_argument('--fromDropbox', action='store_true',
                        help='Direction to synchronize Dropbox')
    parser.add_argument('--fromLocal', action='store_true',
                        help='Direction to synchronize Dropbox')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show all Take default answer on all questions')
    # Parser arguments
    args = parser.parse_args()
    if sum([bool(b) for b in (args.fromDropbox, args.fromLocal)]) > 1:
        print('At most one of --fromDropbox or --fromLocal is allowed')
        sys.exit(2)
    if not args.token:
        print('--token is mandatory')
        sys.exit(2) 
            
    folder = args.folder
    rootdir = os.path.expanduser(args.rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist on your filesystem')
        sys.exit(1)
    elif not os.path.isdir(rootdir):
        print(rootdir, 'is not a folder on your filesystem')
        sys.exit(1)
    # Start updown sync        
    updown = UpDown(args.token, folder, rootdir, verbose=args.verbose)
    
    print("DropboxSync [{}]".format(colored("START", "green")))
    
    if args.fromDropbox:
        updown.syncFromDropbox()
        do_every(args.interval, updown.syncFromDropbox())
    
    if args.fromLocal:
        updown.syncFromLocal()
        # Initialize file and folder observer
        observer = Observer()
        observer.schedule(updown, rootdir, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
# EOF
