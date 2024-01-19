import os


_IMAGE = "dockerhub-prod.kbase.us/kbase:rast_sdk."
_IMAGE += "50b012d9b41b71ba31b30355627cf85f2611bc3e"


CATALOG_GET_MODULE_VERSION = {
    "registration_id": "1553870236585_bab74ed6-4699-47b5-b865-d7130b90f542",
    "release_timestamp": 1554153143124,
    "data_folder": "rast_sdk",
    "released": 1,
    "local_functions": [],
    "timestamp": 1553870236585,
    "notes": "",
    "docker_img_name": _IMAGE,
    "git_commit_hash": "50b012d9b41b71ba31b30355627cf85f2611bc3e",
    "data_version": "0.2",
    "version": "0.1.1",
    "narrative_methods": [
        "reannotate_microbial_genomes",
        "annotate_contigset",
        "annotate_plant_transcripts",
        "annotate_contigsets",
        "reannotate_microbial_genome",
    ],
    "git_url": "https://github.com/kbaseapps/RAST_SDK",
    "released_timestamp": None,
    "release_tags": ["release", "beta"],
    "module_name": "RAST_SDK",
    "dynamic_service": 0,
    "git_commit_message": "Merge a pull",
}

EE2_JOB_PARAMS = {
    u"app_id": u"echo_test/echo_test",
    u"meta": {
        u"cell_id": u"c7fd3baa-69de-4858-90b9-e0332b8371ad",
        u"run_id": u"6331236f-be75-425f-8982-3565cd50242d",
        u"tag": u"beta",
        u"token_id": u"082fc6f3-3d22-48d5-8f9e-bb76ff1022bd",
    },
    u"method": u"echo_test.echo",
    u"params": [
        {u"message": u"test", u"workspace_name": u"scanon:narrative_1559498772483"}
    ],
    u"requested_release": None,
    u"service_ver": u"4b5a37e6fed857c199df65191ba3344a467b8aab",
    u"wsid": 42906,
}


def ee2_list_config(base):
    refdata = os.environ.get("KB_REF_DATA", "/kb/data")
    res = {
        u"auth-service-url": base + u"auth/api/legacy/KBase/Sessions/Login",
        u"auth-service-url-allow-insecure": u"false",
        u"auth-service-url-v2": base + u"auth/api/V2/token",
        u"awe.client.callback.networks": u"docker0,eth0",
        u"awe.client.docker.uri": u"unix:///var/run/docker.sock",
        u"catalog.srv.url": base + u"catalog",
        u"condor.docker.job.timeout.seconds": u"604800",
        u"condor.job.shutdown.minutes": u"10080",
        u"docker.registry.url": u"dockerhub-prod.kbase.us",
        u"ee.server.version": u"0.2.11",
        u"handle-url": base + u"handle_service",
        u"kbase-endpoint": u"https://ci.kbase.us/services",
        u"ref.data.base": refdata,
        u"ref_data_base": refdata,
        u"external-url": base + u"ee2",
        u"shock-url": base + u"shock-api",
        u"srv.wiz.url": base + u"service_wizard",
        u"srv-wiz-url": base + u"service_wizard",
        u"time.before.expiration": u"10",
        u"workspace-url": base + u"ws",
        u"scratch": "/tmp",
    }
    return res

CATALOG_LIST_VOLUME_MOUNTS = [
    {
        "module_name": "mock_app",
        "function_name": "bogus",
        "client_group": "kb_upload",
        "volume_mounts": [
            {
                "host_dir": "/tmp/${username}",
                "container_dir": "/staging",
                "read_only": 1,
            }
        ],
    }
]

CATALOG_GET_SECURE_CONFIG_PARAMS = [
    {
        u"module_name": u"mock_app",
        u"param_name": u"param1",
        u"param_value": u"value1",
        u"version": u"",
    },
    {
        u"is_password": 0,
        u"module_name": u"mock_app",
        u"param_name": u"param2",
        u"param_value": u"value2",
        u"version": u"",
    },
]

AUTH_V2_TOKEN = {
    "type": "Developer",
    "id": "91111111-1bd6-4953-a0dc-a6bb24d5e25c",
    "expires": 1567268700544,
    "created": 1559492700544,
    "name": "20190602",
    "user": "scanon",
    "custom": {},
    "cachefor": 300000,
}
