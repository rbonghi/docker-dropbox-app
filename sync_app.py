"""Syncronization system for APP Dropbox.

Starting point from [1] Use API v2.

[1] https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py
"""

from __future__ import print_function

import argparse
import contextlib
import os, sys, time, logging, datetime
import six
import unicodedata
# How it is work watchdog
# * https://pythonhosted.org/watchdog/quickstart.html#a-simple-example
# * https://stackoverflow.com/questions/32923451/how-to-run-an-function-when-anything-changes-in-a-dir-with-python-watchdog
# * https://stackoverflow.com/questions/46372041/seeing-multiple-events-with-python-watchdog-library-when-folders-are-created
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

if sys.version.startswith('2'):
    input = raw_input  # noqa: E501,F821; pylint: disable=redefined-builtin,undefined-variable,useless-suppression

import dropbox

# OAuth2 access token.
TOKEN = os.environ['DROPBOX_TOKEN'] if "DROPBOX_TOKEN" in os.environ else ""
FOLDER = os.environ['DROPBOX_FOLDER'] if "DROPBOX_FOLDER" in os.environ else "Downloads"
ROOTDIR = os.environ['DROPBOX_ROOTDIR'] if "DROPBOX_ROOTDIR" in os.environ else "~/Downloads"

class UpDown(LoggingEventHandler):

    def __init__(self, token, folder, rootdir, verbose=False):
        self.folder = folder
        self.rootdir = rootdir
        self.verbose = verbose
        if verbose:
            print('Dropbox folder name:', folder)
            print('Local directory:', rootdir)
        self.dbx = dropbox.Dropbox(token)
        
    #def dispatch(self, event):
    #    print("dispatch")
    #def on_any_event(self, event):
    #    print("on_any_event")
        
    def on_modified(self, event):
        print("on_modified")
        # Syncronization from Local to Dropbox
        self.syncFromLocal(option="no")
        
    def sync(self, option="default"):
        """ Sync from dropbox to Local and viceversa
        """
        if os.listdir(self.rootdir):
            self.syncFromLocal(option="no")
        else:
            print("Folder", self.rootdir, "is empty")
        self.syncFromDropBox()

    def storefile(self, res, filename, timedb):
        out = open(filename, 'wb')
        out.write(res)
        out.close()
        # Fix time with md time
        # https://nitratine.net/blog/post/change-file-modification-time-in-python/
        modTime = time.mktime(timedb.timetuple())
        os.utime(filename, (modTime, modTime))
                
    def syncFromDropBox(self, subfolder=""):
        """ Recursive function to download all files from dropbox
        """
        listing = self.list_folder(subfolder)
        for nname in listing:
            md = listing[nname]
            if (isinstance(md, dropbox.files.FileMetadata)):
                path = self.rootdir + subfolder + "/" + nname
                res = self.download(subfolder, nname)
                # Store file in folder
                if os.path.exists(path):
                    mtime = os.path.getmtime(path)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(path)
                    #print("MDTime file:", mtime_dt)
                    #print("MDTime DropBox:", md.client_modified)
                    if(mtime_dt == md.client_modified and size == md.size):
                        print(nname, 'is already synced [stats match]')
                    else:
                        self.storefile(res, path, md.client_modified)
                else:
                    self.storefile(res, path, md.client_modified)
            if (isinstance(md, dropbox.files.FolderMetadata)):
                path = self.rootdir + subfolder + "/" + nname
                if self.verbose: print('Descending into', nname, '...')
                if not os.path.exists(path):
                    os.makedirs(path)
                self.syncFromDropBox(subfolder=subfolder + "/" + nname)

    def syncFromLocal(self, option="default"):

        for dn, dirs, files in os.walk(self.rootdir):
            subfolder = dn[len(self.rootdir):].strip(os.path.sep)
            listing = self.list_folder(subfolder)
            if self.verbose: print('Descending into', subfolder, '...')

            # First do all the files.
            for name in files:
                fullname = os.path.join(dn, name)
                if not isinstance(name, six.text_type):
                    name = name.decode('utf-8')
                nname = unicodedata.normalize('NFC', name)
                if name.startswith('.'):
                    print('Skipping dot file:', name)
                elif name.startswith('@') or name.endswith('~'):
                    print('Skipping temporary file:', name)
                elif name.endswith('.pyc') or name.endswith('.pyo'):
                    print('Skipping generated file:', name)
                elif nname in listing:
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
                            if self.yesno('Refresh %s' % name, False, option):
                                self.upload(fullname, subfolder, name, overwrite=True)
                elif self.yesno('Upload %s' % name, True, option):
                    self.upload(fullname, subfolder, name)

            # Then choose which subdirectories to traverse.
            keep = []
            for name in dirs:
                if name.startswith('.'):
                    print('Skipping dot directory:', name)
                elif name.startswith('@') or name.endswith('~'):
                    print('Skipping temporary directory:', name)
                elif name == '__pycache__':
                    print('Skipping generated directory:', name)
                elif self.yesno('Descend into %s' % name, True, option):
                    print('Keeping directory:', name)
                    keep.append(name)
                else:
                    print('OK, skipping directory:', name)
            dirs[:] = keep
            
    def yesno(self, message, default, option):
        if option == "default":
            if self.verbose: print(message + '? [auto]', 'Y' if default else 'N')
            return default
        if option == "yes":
            if self.verbose: print(message + '? [auto] YES')
            return True
        if option == "no":
            if self.verbose: print(message + '? [auto] NO')
            return False

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
            with stopwatch('list_folder'):
                res = self.dbx.files_list_folder(path, recursive=recursive)
        except dropbox.exceptions.ApiError as err:
            print('Folder listing failed for', path, '-- assumed empty:', err)
            return {}
        else:
            rv = {}
            for entry in res.entries:
                rv[entry.name] = entry
            return rv

    def download(self, subfolder, name):
        """Download a file.

        Return the bytes of the file, or None if it doesn't exist.
        """
        path = '/%s/%s/%s' % (self.folder, subfolder.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        with stopwatch('download'):
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
        path = '/%s/%s/%s' % (self.folder, subfolder.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(fullname)
        with open(fullname, 'rb') as f:
            data = f.read()
        with stopwatch('upload %d bytes' % len(data)):
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

@contextlib.contextmanager
def stopwatch(message):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        print('Total elapsed time for %s: %.3f' % (message, t1 - t0))

"""Main program.

Parse command line, then iterate over files and directories under
rootdir and upload all files.  Skips some temporary files and
directories, and avoids duplicate uploads by comparing size and
mtime with the server.
"""
if __name__ == '__main__':
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
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Answer yes to all questions')
    parser.add_argument('--no', '-n', action='store_true',
                        help='Answer no to all questions')
    parser.add_argument('--default', '-d', action='store_true',
                        help='Take default answer on all questions')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show all Take default answer on all questions')
    # Parser arguments
    args = parser.parse_args()
    if sum([bool(b) for b in (args.yes, args.no, args.default)]) > 1:
        print('At most one of --yes, --no, --default is allowed')
        sys.exit(2)
    if not args.token:
        print('--token is mandatory')
        sys.exit(2)  
            
    if args.yes:
        option = "yes"
    elif args.no:
        option = "no"
    else:
        option = "default"
            
    folder = args.folder
    rootdir = os.path.expanduser(args.rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist on your filesystem')
        sys.exit(1)
    elif not os.path.isdir(rootdir):
        print(rootdir, 'is not a folder on your filesystem')
        sys.exit(1)
    # Start updown sync        
    updown = UpDown(args.token, folder, rootdir, args.verbose)
    
    updown.syncFromDropBox()
    
    sys.exit(1)
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
