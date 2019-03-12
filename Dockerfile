FROM python:3-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    git \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/dropbox/dropbox-sdk-python.git \
    && cd dropbox-sdk-python \
    && python setup.py install
    
ENV DROPBOX_TOKEN=""

VOLUME ["/dropbox"]

#COPY sync_app.py /root

WORKDIR "/root"

ENTRYPOINT ["python", "sync_app.py", "-y" ]
CMD [ "/", "/dropbox" ]

