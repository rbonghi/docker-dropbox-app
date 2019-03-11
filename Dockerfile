FROM python:3-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    git \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/dropbox/dropbox-sdk-python.git \
    && cd dropbox-sdk-python \
    && python setup.py install
    
ENV TOKEN=""

WORKDIR "/dropbox-sdk-python/example"

VOLUME ["/shared_data"]

ENTRYPOINT ["python", "updown.py", "--token", "$TOKEN" ]
CMD ["/", "/shared_data"]
