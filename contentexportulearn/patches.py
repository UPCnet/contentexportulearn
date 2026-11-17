# -*- coding: utf-8 -*-
from collective.exportimport.export_other import safe_bytes
from App.config import getConfiguration
from collective.exportimport import _
from collective.exportimport import config
from plone import api
from plone.namedfile.interfaces import INamedFile
from plone.restapi.serializer.converters import json_compatible as restapi_json_compatible

import base64
import json
import logging
import os

logger = logging.getLogger(__name__)


def json_compatible(value, context=None):
    """json_compatible de plone.restapi + ficheros/imágenes (NamedFile, NamedBlobImage…).

    Sustituye a ``collective.exportimport.export_other.json_compatible``: el export de
    portlets (``export_local_portlets``) llama a json_compatible con el valor de cada
    campo y plone.restapi 4.x no tiene conversor para NamedBlobImage → TypeError y
    @@export_all se cortaba. Formato = el que acepta el IFieldDeserializer de
    plone.restapi en el import (ushare6).
    """
    if INamedFile.providedBy(value):
        return {
            u"data": base64.b64encode(value.data).decode("ascii"),
            u"encoding": u"base64",
            u"filename": value.filename,
            u"content-type": value.contentType,
        }
    return restapi_json_compatible(value, context)

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