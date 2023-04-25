FROM python:3.9

ADD . /src

WORKDIR "/src"

RUN pip install -r requirements.txt


CMD [ "python3", "-m", "JobRunner.Callback"]
