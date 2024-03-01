FROM python:3.9

ADD requirements.txt /src/requirements.txt

WORKDIR "/src"


RUN pip install -r requirements.txt
ADD . /src

EXPOSE 9999

ENV IN_CONTAINER=1

CMD [ "python3", "-m", "JobRunner.Callback"]
