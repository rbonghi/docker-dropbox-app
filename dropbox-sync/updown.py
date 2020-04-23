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

#from watchdog.events import LoggingEventHandler
from watchdog.events import PatternMatchingEventHandler

import dropbox

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
        if ignore_files:
            print("Ignore dropbox files:", colored(ignore_files, "red"))
        
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
            dirs[:] = [d for d in dirs if not re.match(self.excludes, d)]
            # exclude files
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
                else:
                    # Upload all new files
                    print(name, 'Upload')
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
            f = open(fullname, 'rb')
            file_size = os.path.getsize(fullname)
            
            if file_size <= CHUNK_SIZE:
                data = f.read()
                with self.stopwatch('upload %d bytes' % file_size):
                    try:
                        res = self.dbx.files_upload(
                            data, path, mode,
                            client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                            mute=True)
                    except dropbox.exceptions.ApiError as err:
                        print('*** API error', err)
                        return None
            else:
                upload_session_start_result = self.dbx.files_upload_session_start(f.read(CHUNK_SIZE))
                cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id,
                                                           offset=f.tell())
                commit = dropbox.files.CommitInfo(path=path)
                # Upload file
                with self.stopwatch('upload %d bytes' % file_size):
                    while f.tell() < file_size:
                        if ((file_size - f.tell()) <= CHUNK_SIZE):
                            res = self.dbx.files_upload_session_finish(f.read(CHUNK_SIZE),
                                                            cursor,
                                                            commit)
                        else:
                            self.dbx.files_upload_session_append(f.read(CHUNK_SIZE),
                                                            cursor.session_id,
                                                            cursor.offset)
                            cursor.offset = f.tell()
                            
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
# EOF
