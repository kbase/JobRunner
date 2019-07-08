class job:
    def __init__(self):
        self.job_id = None
        self.job_params = None


j1 = job()
j1.job_id = 'job_5c6c8aa9e4b0f2ea4c0bac74'
j1.job_params = [
    {'method': 'simpleapp.simple_add',
     'params': [{'base_number': 0, 'workspace_name': 'bsadkhin:narrative_1549663862852'}],
     'service_ver': 'f5a7586776c31b05ae3cc6923c2d46c25990d20a',
     'app_id': 'simpleapp/example_method',
     'meta':
         {'run_id': 'd09f17d7-da43-437d-a3a3-d4ebe12d5de6',
          'token_id': '2248ed53-14c8-46d7-92b0-57fab5d0b26d', 'tag': 'dev',
          'cell_id': '84f00217-921e-4b83-9b9a-3ea0d2b762b9'},
     'wsid': 40530, 'requested_release': None},
    {'workspace.srv.url': 'https://ci.kbase.us/services/ws',
     'jobstatus.srv.url': 'https://ci.kbase.us/services/userandjobstate/',
     'docker.registry.url': 'dockerhub-ci.kbase.us',
     'awe.client.docker.uri': 'unix:///var/run/docker.sock',
     'catalog.srv.url': 'https://ci.kbase.us/services/catalog',
     'ref.data.base': '/kbase/data/sdk/ci/refdata', 'awe.client.callback.networks': 'docker0,eth0',
     'auth-service-url': 'https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login',
     'auth.service.url.v2': 'https://ci.kbase.us/services/auth/api/V2/token',
     'time.before.expiration': '10', 'condor.job.shutdown.minutes': '10080',
     'condor.docker.job.timeout.seconds': '604800',
     'kbase.endpoint': 'https://ci.kbase.us/services',
     'self.external.url': 'https://ci.kbase.us/services/njs_wrapper',
     'shock.url': 'https://ci.kbase.us/services/shock-api',
     'handle.url': 'https://ci.kbase.us/services/handle_service',
     'srv.wiz.url': 'https://ci.kbase.us/services/service_wizard', 'ee.server.version': '0.2.11',
     'auth-service-url-allow-insecure': 'false'}
]
