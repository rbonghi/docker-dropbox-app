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

import argparse
import sys
import os


# OAuth2 access token.
TOKEN = os.environ['DROPBOX_TOKEN'] if "DROPBOX_TOKEN" in os.environ else ""
FOLDER = os.environ['DROPBOX_FOLDER'] if "DROPBOX_FOLDER" in os.environ else "Downloads"
ROOTDIR = os.environ['DROPBOX_ROOTDIR'] if "DROPBOX_ROOTDIR" in os.environ else "~/Downloads"
INTERVAL = int(os.environ['DROPBOX_INTERVAL']) if "DROPBOX_INTERVAL" in os.environ else 60


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def ok():
        return bcolors.OKGREEN + "OK" + bcolors.ENDC

    @staticmethod
    def warning():
        return bcolors.WARNING + "WARN" + bcolors.ENDC

    @staticmethod
    def fail():
        return bcolors.FAIL + "ERR" + bcolors.ENDC


def main():
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
    if sum([bool(b) for b in (args.fromDropbox, args.fromLocal)]) != 1:
        print('Select one of --fromDropbox or --fromLocal')
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
    ###############updown = UpDown(args.token, folder, rootdir, verbose=args.verbose)
    
    print(f"DropboxSync [{bcolors.OKGREEN}START{bcolors.ENDC}]")
    
    if args.fromDropbox:
        updown.syncFromDropbox()
        print(f"{bcolors.OKGREEN}Ready to sync{bcolors.ENDC}")
        ###############do_every(args.interval, updown.syncFromDropbox())
    
    if args.fromLocal:
        if not os.listdir(rootdir):
            cprint("Directory is empty, start first download", "yellow")
            updown.syncFromDropbox()
        else:
            updown.syncFromLocal()
        cprint("Ready to sync", "green")
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


if __name__ == '__main__':
    main()
# EOF
