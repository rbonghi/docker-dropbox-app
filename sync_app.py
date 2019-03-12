"""Upload the contents of your Downloads folder to Dropbox.

This is an example app for API v2.

Idea from https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py
"""

from __future__ import print_function

import argparse
import contextlib
import os, sys, time, datetime
import six
import unicodedata

if sys.version.startswith('2'):
    input = raw_input  # noqa: E501,F821; pylint: disable=redefined-builtin,undefined-variable,useless-suppression

import dropbox

# OAuth2 access token.
TOKEN = os.environ['DROPBOX_TOKEN'] if "DROPBOX_TOKEN" in os.environ else ""

class UpDown:

    def __init__(self, token, folder, rootdir, verbose=False):
        self.folder = folder
        self.rootdir = rootdir
        self.verbose = verbose
        if verbose:
            print('Dropbox folder name:', folder)
            print('Local directory:', rootdir)
        self.dbx = dropbox.Dropbox(token)
        
    def sync(self, option="default"):
        if not os.listdir(self.rootdir):
            print("Folder", self.rootdir, "is empty")
            self.syncFromDB()
        else:
            print("Sync data")
            #self.syncFromDB()
        
    def syncFromDB(self):
        print("Sync from Dropbox")

    def syncFromLocal(self, option="default"):

        for dn, dirs, files in os.walk(self.rootdir):
            subfolder = dn[len(self.rootdir):].strip(os.path.sep)
            listing = self.list_folder(subfolder)
            print('Descending into', subfolder, '...')

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
                elif yesno('Descend into %s' % name, True, args):
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

    def list_folder(self, subfolder):
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
                res = self.dbx.files_list_folder(path)
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
    parser = argparse.ArgumentParser(description='Sync ~/dropbox to Dropbox')
    parser.add_argument('folder', nargs='?', default='Downloads',
                        help='Folder name in your Dropbox')
    parser.add_argument('rootdir', nargs='?', default='~/Downloads',
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
            
    verbose = False
                        
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
    updown = UpDown(args.token, folder, rootdir, verbose)
    updown.sync(option)
# EOF
