# -*- coding: utf-8 -*-
import unittest
from unittest.mock import create_autospec

from JobRunner.CatalogCache import CatalogCache

from copy import deepcopy
from mock_data import (
    CATALOG_GET_MODULE_VERSION,
    CATALOG_LIST_VOLUME_MOUNTS,
    CATALOG_GET_SECURE_CONFIG_PARAMS,
)
from clients.CatalogClient import Catalog


class CatalogCacheTest(unittest.TestCase):

    def get_mocks(self):
        catalog = create_autospec(Catalog, spec_set=True, instance=True)
        return CatalogCache(catalog, token="bogus"), catalog

    def test_cache(self):
        cc, catalog  = self.get_mocks()
        catalog.get_module_version.return_value = CATALOG_GET_MODULE_VERSION
        out = cc.get_module_info("bogus", "method")
        self.assertIn("git_commit_hash", out)
        self.assertIn("cached", out)
        self.assertFalse(out["cached"])
        out = cc.get_module_info("bogus", "method")
        self.assertIn("git_commit_hash", out)
        self.assertIn("cached", out)
        self.assertTrue(out["cached"])
        self.assertIn("secure_config_params", out)

    def test_secure_params(self):
        cc, catalog  = self.get_mocks()
        catalog.get_module_version.return_value = CATALOG_GET_MODULE_VERSION
        catalog.get_secure_config_params.return_value = (
            CATALOG_GET_SECURE_CONFIG_PARAMS
        )
        out = cc.get_module_info("bogus", "method")
        self.assertIn("git_commit_hash", out)
        self.assertIn("cached", out)
        self.assertFalse(out["cached"])
        out = cc.get_module_info("bogus", "method")
        self.assertIn("secure_config_params", out)
        self.assertGreater(len(out["secure_config_params"]), 0)

    def test_volume(self):
        cc, catalog  = self.get_mocks()
        vols = deepcopy(CATALOG_LIST_VOLUME_MOUNTS)
        catalog.list_volume_mounts.return_value = vols
        out = cc.get_volume_mounts("bogus", "method", "upload")
        self.assertTrue(len(out) > 0)
        self.assertIn("host_dir", out[0])
