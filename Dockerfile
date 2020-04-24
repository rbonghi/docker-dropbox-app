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

FROM python:3-alpine
# Build-time metadata as defined at http://label-schema.org
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
LABEL org.label-schema.build-date=$BUILD_DATE \
        org.label-schema.name="docker-dropbox-app" \
        org.label-schema.description="Automatic sync folder by a dropbox app" \
        org.label-schema.url="https://rnext.it/" \
        org.label-schema.vcs-ref=$VCS_REF \
        org.label-schema.vcs-url="https://github.com/rbonghi/docker-dropbox-app" \
        org.label-schema.vendor="rbonghi" \
        org.label-schema.version=$VERSION \
        org.label-schema.schema-version="1.0"

# Install requirements
COPY requirements.txt /root
RUN pip install -r /root/requirements.txt
# Define default dropbox folder in docker
ENV DROPBOX_TOKEN=""
ENV DROPBOX_FOLDER="/"
ENV DROPBOX_ROOTDIR="/dropbox"

VOLUME ["/dropbox"]

COPY . /root

WORKDIR "/root"

RUN python setup.py install

ENTRYPOINT ["dbsync" ]
