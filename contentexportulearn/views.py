# -*- coding: UTF-8 -*-
from contentexportulearn.interfaces import IContentexportLayer
from plone import api
from Products.Five import BrowserView
from ZODB.POSException import ConflictError
from zope.interface import alsoProvides

import logging

logger = logging.getLogger(__name__)

TYPES_TO_EXPORT = []
PATH = ''


class ExportAll(BrowserView):

    def __call__(self):
        request = self.request
        if not request.form.get("form.submitted", False):
            return self.index()

        qi = api.portal.get_tool("portal_quickinstaller")
        if not qi.isProductInstalled("contentimport"):
            qi.installProducts(["contentimport"])
            alsoProvides(request, IContentexportLayer)

        portal = api.portal.get()

        export_name = "export_content"
        logger.info("Start {}".format(export_name))
        view = api.content.get_view(export_name, portal, request)
        exported_types = TYPES_TO_EXPORT
        PATH = "/".join(portal.getPhysicalPath())
        request.form["form.submitted"] = True
        # Modificado para exportar e importar cada contenido en un fichero json "download_to_server=2"
        # view(portal_type=exported_types, include_blobs=1, download_to_server=True, path=PATH)
        view(portal_type=exported_types, include_blobs=1, download_to_server=2, path=PATH)
        logger.info("Finished {}".format(export_name))

        other_exports = [
            "export_relations",
            "export_members",
            "export_translations",
            "export_localroles",
            "export_ordering",
            "export_defaultpages",
            "export_discussion",
            "export_portlets",
            "export_redirects",
            "export_settings",
            "export_controlpanels",
            "export_portalrolemanager",
            "export_user_catalog",
        ]

        # Un export que falla (p. ej. portlets con datos no serializables) no debe
        # dejar sin ejecutar los siguientes (settings, portalrolemanager, user_catalog…)
        failed = []
        for export_name in other_exports:
            try:
                export_view = api.content.get_view(export_name, portal, request)
                request.form["form.submitted"] = True
                # store each result in var/instance/export_xxx.json
                export_view(download_to_server=True)
            except ConflictError:
                raise
            except Exception:
                logger.exception("export_all: ha fallado %s, sigo con el resto", export_name)
                failed.append(export_name)

        if failed:
            msg = "export_all terminado con errores en: {}".format(", ".join(failed))
            logger.error(msg)
            api.portal.show_message(msg, request, type="error")
        logger.info("Finished export_all")
        # Important! Redirect to prevent infinite export loop :)
        return self.request.response.redirect(self.context.absolute_url())
