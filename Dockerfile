FROM python:3.9

ADD requirements.txt /src/requirements.txt

WORKDIR "/src"

RUN pip install -r requirements.txt
ADD . /src

CMD [ "python3", "-m", "JobRunner.Callback"]
EXPOSE 9999
