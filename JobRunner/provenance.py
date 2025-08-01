from datetime import datetime, timezone


class Provenance(object):

    def __init__(self, params):
        # Can generate provenance from either job input or a workspace ProvenanceAction
        # job input takes precedence
        # We might want to be more strict about provenance contents. For now it's pretty forgiving
        if "." in params.get("method", ""):
            (module, method) = params["method"].split(".")
        else:
            module = params.get("service")
            method = params.get("method")
        self.actions = dict()
        t = datetime.now(timezone.utc).astimezone().replace(microsecond=0)
        desc = "KBase SDK method run via the KBase Execution Engine"
        # TODO may need to check that service-ver is set
        self.prov = {
            "time": params.get("time", t.isoformat()),
            "service": module,
            "service_ver": params.get("service_ver", "dev"),
            "method": method,
            "method_params": params.get("params", params.get("method_params", [])),
            "input_ws_objects": params.get(
                "source_ws_objects", params.get("input_ws_objects", [])
            ),
            "subactions": params.get("subactions", []),
            "description": params.get("description", desc),
        }

    def add_subaction(self, data):
        if data["name"] not in self.actions:
            self.actions[data["name"]] = data
            action = data
            self.prov["subactions"].append(action)

    def get_prov(self):
        return [self.prov]
