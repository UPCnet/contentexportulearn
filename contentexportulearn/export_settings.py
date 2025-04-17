# -*- coding: UTF-8 -*-
import logging

from collective.exportimport.export_other import BaseExport
from plone import api
from plone.restapi.serializer.converters import json_compatible

logger = logging.getLogger(__name__)

class ExportSettings(BaseExport):
    """Export various settings for haiku sites
    """

    def __call__(self, download_to_server=False):
        self.title = "Export installed addons various settings"
        self.download_to_server = download_to_server
        if not self.request.form.get("form.submitted", False):
            return self.index()

        data = self.export_settings()
        self.download(data)

    def export_settings(self):
        results = {}
        addons = []
        qi = api.portal.get_tool("portal_quickinstaller")
        for product in qi.listInstalledProducts():
            if product["id"].startswith("genweb."):
                addons.append(product["id"])
        results["addons"] = addons

        return results
