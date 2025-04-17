# -*- coding: utf-8 -*-
from collective.exportimport.export_other import safe_bytes
from App.config import getConfiguration
from collective.exportimport import _
from collective.exportimport import config
from plone import api

import json
import logging
import os

logger = logging.getLogger(__name__)

def download(self, data):
    filename = u"{}.json".format(self.__name__)
    if not data:
        msg = _(u"No data to export for {}").format(self.__name__)
        logger.info(msg)
        api.portal.show_message(msg, self.request)
        return self.request.response.redirect(self.request["ACTUAL_URL"])

    if self.download_to_server:
        directory = config.CENTRAL_DIRECTORY
        if directory:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info("Created central export/import directory %s", directory)
        else:
            cfg = getConfiguration()
            portal = api.portal.get()
            directory_import = cfg.clienthome + "/import"
            directory = cfg.clienthome + "/import/" + portal.id
        filepath = os.path.join(directory, filename)
        with open(filepath, "w") as f:
            json.dump(data, f, sort_keys=True, indent=4)
        msg = _(u"Exported to {}").format(filepath)
        logger.info(msg)
        api.portal.show_message(msg, self.request)
        return self.request.response.redirect(self.request["ACTUAL_URL"])

    else:
        data = json.dumps(data, sort_keys=True, indent=4)
        data = safe_bytes(data)
        response = self.request.response
        response.setHeader("content-type", "application/json")
        response.setHeader("content-length", len(data))
        response.setHeader(
            "content-disposition",
            'attachment; filename="{0}"'.format(filename),
        )
        return response.write(data)