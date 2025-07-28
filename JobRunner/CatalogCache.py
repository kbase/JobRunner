from clients.CatalogClient import Catalog


class CatalogCache(object):

    def __init__(self, catalog: Catalog, token: str = None):
        """
        Initialize the cache. If the catalog client has a token, it must be a catalog admin
        token.
        """
        self.catalog = catalog
        # TODO CODE add a method to SDK clients to get the token, then use that here
        self.has_admin_token = bool(token)
        self.module_cache = dict()

    def get_volume_mounts(self, module, method, cgroup):
        if not self.has_admin_token:
            return []
        req = {"module_name": module, "function_name": method, "client_group": cgroup}
        resp = self.catalog.list_volume_mounts(req)
        if len(resp) > 0:
            return resp[0]["volume_mounts"]
        else:
            return []

    def get_module_info(self, module, version):
        # Look up the module info
        if module not in self.module_cache:
            req = {"module_name": module}
            if version is not None:
                req["version"] = version
            # Get the image version from the catalog and cache it
            module_info = self.catalog.get_module_version(req)
            # Lookup secure params
            sp = []
            if self.has_admin_token:
                req["load_all_versions"] = 0
                sp = self.catalog.get_secure_config_params(req)
            module_info["secure_config_params"] = sp
            module_info["cached"] = False
            self.module_cache[module] = module_info
        else:
            # Use the cache
            module_info = self.module_cache[module]
            module_info["cached"] = True

        return module_info
