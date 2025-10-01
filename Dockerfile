FROM python:3.13.7

RUN apt update \
    && apt install -y tini \
    && rm -rf /var/lib/apt/lists/* 

# install uv
RUN pip install --upgrade pip && \
    pip install uv==0.8.2

# install deps
RUN mkdir /uvinstall
WORKDIR /uvinstall
COPY pyproject.toml uv.lock .python-version ./
ENV UV_PROJECT_ENVIRONMENT=/usr/local/
RUN uv sync --locked --inexact --no-dev

WORKDIR "/src"
ADD . /src

EXPOSE 9999

ENV IN_CONTAINER=1

CMD [ "tini", "--", "python3", "-m", "JobRunner.Callback" ]
