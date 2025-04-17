# -*- coding: UTF-8 -*-
from collective.exportimport.export_content import safe_bytes
from collective.exportimport.export_content import ExportContent
from zope.annotation.interfaces import IAnnotations
from plone.restapi.interfaces import IJsonCompatible

from App.config import getConfiguration
from collective.exportimport import _
from collective.exportimport import config
from collective.exportimport.interfaces import IBase64BlobsMarker
from collective.exportimport.interfaces import IMigrationMarker
from collective.exportimport.interfaces import IPathBlobsMarker
from collective.exportimport.interfaces import IRawRichTextMarker
from operator import itemgetter
from plone import api
from plone.app.layout.viewlets.content import ContentHistoryViewlet
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.serializer.converters import json_compatible
from plone.uuid.interfaces import IUUID
from Products.CMFPlone.interfaces.constrains import ENABLED
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.schema import getFields

import json
import logging
import os
import pkg_resources
import six
import tempfile

import logging

logger = logging.getLogger(__name__)

TYPES_TO_EXPORT = [
    "Folder",
    "Document",
    "Event",
    "File",
    "Image",
    "Link",
    "News Item",
    "Topic",
    "Collection",
    "EasyForm",
    "Banner",
    "BannerContainer",
    "genweb.upc.documentimage",
    "genweb.upc.subhome",
    "LIF",
    "LRF",
    "Logos_Container",
    "Logos_Footer",
    "packet",
    "genweb.tfemarket.market",
    "genweb.tfemarket.offer",
    "genweb.tfemarket.application",
    "Window",
    "genweb.ens.acord",
    "genweb.ens.acta_reunio",
    "genweb.ens.carrec_upc",
    "genweb.ens.carrec",
    "genweb.ens.persona_directiu",
    "genweb.ens.contenidor_ens",
    "genweb.ens.contenidor_representants",
    "genweb.ens.conveni",
    "genweb.ens.document_interes",
    "genweb.ens.escriptura_publica",
    "genweb.ens.documentacio",
    "genweb.ens.ens",
    "genweb.ens.estatut",
    "genweb.ens.organ",
    "genweb.ens.persona_contacte",
    "genweb.ens.representant",
    "genweb.ens.unitat",
    "Scholarship",
    "serveitic",
    "notificaciotic",
    "documentrrhh",
    "Noticia_actualidad",
    "Flash_informativo",
    "Docmigrat",
    "Job_Posting",
    "privateFolder",
    "AppFile"
]

PATH = ''

# Content for test-migrations
PATHS_TO_EXPORT = []

MARKER_INTERFACES_TO_EXPORT = []

ANNOTATIONS_TO_EXPORT = [
    "genweb.portlets.span.genweb.portlets.HomePortletManager1",
    "genweb.portlets.span.genweb.portlets.HomePortletManager2",
    "genweb.portlets.span.genweb.portlets.HomePortletManager3",
    "genweb.portlets.span.genweb.portlets.HomePortletManager4",
    "genweb.portlets.span.genweb.portlets.HomePortletManager5",
    "genweb.portlets.span.genweb.portlets.HomePortletManager6",
    "genweb.portlets.span.genweb.portlets.HomePortletManager7",
    "genweb.portlets.span.genweb.portlets.HomePortletManager8",
    "genweb.portlets.span.genweb.portlets.HomePortletManager9",
    "genweb.portlets.span.genweb.portlets.HomePortletManager10",
    "genweb.core.important",
    "genweb.packets.fields",
    "genweb.packets.type",
    "genweb.packets.mapui",
]

ANNOTATIONS_KEY = "exportimport.annotations"

MARKER_INTERFACES_KEY = "exportimport.marker_interfaces"


class CustomExportContent(ExportContent):

    QUERY = {
    }

    DROP_PATHS = [
        PATH + '/templates',
        PATH + '/es/shared',
        PATH + '/en/shared',
        PATH + '/per_ubicar',
    ]

    DROP_UIDS = [
    ]

    def __call__(
        self,
        portal_type=None,
        path=None,
        depth=-1,
        include_blobs=1,
        download_to_server=False,
        migration=True,
        include_revisions=False,
        write_errors=False
    ):
        self.portal_type = portal_type or []
        if isinstance(self.portal_type, str):
            self.portal_type = [self.portal_type]
        self.migration = migration
        self.path = path or "/".join(self.context.getPhysicalPath())

        self.depth = int(depth)
        self.depth_options = (
            ("-1", _(u"unlimited")),
            ("0", "0"),
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4", "4"),
            ("5", "5"),
            ("6", "6"),
            ("7", "7"),
            ("8", "8"),
            ("9", "9"),
            ("10", "10"),
        )
        self.include_blobs = int(include_blobs)
        self.include_blobs_options = (
            ("0", _(u"as download urls")),
            ("1", _(u"as base-64 encoded strings")),
            ("2", _(u"as blob paths")),
        )
        self.include_revisions = include_revisions
        self.write_errors = write_errors or self.request.form.get("write_errors")

        self.update()

        if not self.request.form.get("form.submitted", False):
            return self.template()

        if not self.portal_type:
            api.portal.show_message(
                _(u"Select at least one type to export"),
                self.request)
            return self.template()

        if self.include_blobs == 1:
            # Add marker-interface to request to use our custom serializers
            alsoProvides(self.request, IBase64BlobsMarker)
        elif self.include_blobs == 2:
            # Add marker interface to export blob paths
            alsoProvides(self.request, IPathBlobsMarker)
        else:
            # Use the default plone.restapi serializer,
            # which gives a download url.
            pass

        if self.migration:
            # Add marker-interface to request to use custom serializers
            alsoProvides(self.request, IMigrationMarker)

        # to get a useful filename...
        if self.portal_type and len(self.portal_type) == 1:
            filename = self.portal_type[0]
        else:
            filename = self.path.split("/")[-1]
        filename = "{}.json".format(filename)

        self.errors = []
        content_generator = self.export_content()

        number = 0

        # Export each item to a separate json-file
        if download_to_server == 2:
            directory = config.CENTRAL_DIRECTORY
            if directory:
                if not os.path.exists(directory):
                    os.makedirs(directory)
                    logger.info("Created central export/import directory %s", directory)
            else:
                cfg = getConfiguration()
                # directory = cfg.clienthome
                portal = api.portal.get()
                directory_import = cfg.clienthome + "/import"
                directory = cfg.clienthome + "/import/" + portal.id
                if directory:
                    if not os.path.exists(directory):
                        os.makedirs(directory)
                        logger.info(
                            "Created central export/import directory %s", directory)

            # Use the filename (Plone.json) as target for files (Plone/1.json)
            directory = os.path.join(directory, filename[:-5])
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info("Created directory to hold content: %s", directory)

            self.start()
            for number, datum in enumerate(content_generator, start=1):
                filename = "{}.json".format(number)
                filepath = os.path.join(directory, filename)
                with open(filepath, "w") as f:
                    json.dump(datum, f, sort_keys=True, indent=4)
            if number:
                if self.errors and self.write_errors:
                    errors = {"unexported_paths": self.errors}
                    with open(os.path.join(directory, "errors.json"), "w") as f:
                        json.dump(errors, f, indent=4)
            msg = _(u"Exported {} items ({}) to {} with {} errors").format(
                number, ", ".join(self.portal_type), directory, len(self.errors)
            )
            logger.info(msg)
            api.portal.show_message(msg, self.request)

            if self.include_blobs == 1:
                # remove marker interface
                noLongerProvides(self.request, IBase64BlobsMarker)
            elif self.include_blobs == 2:
                noLongerProvides(self.request, IPathBlobsMarker)
            self.finish()
            self.request.response.redirect(self.request["ACTUAL_URL"])

        # Export all items into one json-file in the filesystem
        elif download_to_server:
            directory = config.CENTRAL_DIRECTORY
            if directory:
                if not os.path.exists(directory):
                    os.makedirs(directory)
                    logger.info("Created central export/import directory %s", directory)
            else:
                cfg = getConfiguration()
                directory = cfg.clienthome
            filepath = os.path.join(directory, filename)
            with open(filepath, "w") as f:
                self.start()
                for number, datum in enumerate(content_generator, start=1):
                    if number == 1:
                        f.write("[")
                    else:
                        f.write(",")
                    json.dump(datum, f, sort_keys=True, indent=4)
                if number:
                    if self.errors and self.write_errors:
                        f.write(",")
                        errors = {"unexported_paths": self.errors}
                        json.dump(errors, f, indent=4)
                    f.write("]")
            msg = _(u"Exported {} items ({}) as {} to {} with {} errors").format(
                number, ", ".join(self.portal_type), filename, filepath, len(self.errors)
            )
            logger.info(msg)
            api.portal.show_message(msg, self.request)

            if self.include_blobs == 1:
                # remove marker interface
                noLongerProvides(self.request, IBase64BlobsMarker)
            elif self.include_blobs == 2:
                noLongerProvides(self.request, IPathBlobsMarker)
            self.finish()
            self.request.response.redirect(self.request["ACTUAL_URL"])

        # Export as one json-file through the browser
        else:
            with tempfile.TemporaryFile(mode="w+") as f:
                self.start()
                for number, datum in enumerate(content_generator, start=1):
                    if number == 1:
                        f.write("[")
                    else:
                        f.write(",")
                    json.dump(datum, f, sort_keys=True, indent=4)
                if number:
                    if self.errors and self.write_errors:
                        f.write(",")
                        errors = {"unexported_paths": self.errors}
                        json.dump(errors, f, indent=4)
                    f.write("]")
                msg = _(u"Exported {} {} with {} errors").format(
                    number, self.portal_type, len(self.errors))
                logger.info(msg)
                api.portal.show_message(msg, self.request)
                response = self.request.response
                response.setHeader("content-type", "application/json")
                response.setHeader("content-length", f.tell())
                response.setHeader(
                    "content-disposition",
                    'attachment; filename="{0}"'.format(filename),
                )
                if self.include_blobs == 1:
                    # remove marker interface
                    noLongerProvides(self.request, IBase64BlobsMarker)
                elif self.include_blobs == 2:
                    noLongerProvides(self.request, IPathBlobsMarker)
                f.seek(0)
                self.finish()
                return response.write(safe_bytes(f.read()))

        # Codigo antiguo BORRAR
        # if download_to_server:
        #     directory = config.CENTRAL_DIRECTORY
        #     if directory:
        #         if not os.path.exists(directory):
        #             os.makedirs(directory)
        #             logger.info("Created central export/import directory %s", directory)
        #     else:
        #         cfg = getConfiguration()
        #         #directory = cfg.clienthome
        #         portal = api.portal.get()
        #         directory_import = cfg.clienthome + "/import"
        #         directory = cfg.clienthome + "/import/" + portal.id
        #         if directory:
        #             if not os.path.exists(directory):
        #                 os.makedirs(directory)
        #                 logger.info("Created central export/import directory %s", directory)

        #     filepath = os.path.join(directory, filename)
        #     with open(filepath, "w") as f:
        #         self.start()
        #         for number, datum in enumerate(content_generator, start=1):
        #             if number == 1:
        #                 f.write("[")
        #             else:
        #                 f.write(",")
        #             json.dump(datum, f, sort_keys=True, indent=4)
        #         if number:
        #             if self.errors and self.write_errors:
        #                 f.write(",")
        #                 errors = {"unexported_paths": self.errors}
        #                 json.dump(errors, f, indent=4)
        #             f.write("]")
        #     msg = _(u"Exported {} items ({}) as {} to {}").format(
        #         number, ", ".join(self.portal_type), filename, filepath
        #     )
        #     logger.info(msg)
        #     api.portal.show_message(msg, self.request)

        #     if self.include_blobs == 1:
        #         # remove marker interface
        #         noLongerProvides(self.request, IBase64BlobsMarker)
        #     elif self.include_blobs == 2:
        #         noLongerProvides(self.request, IPathBlobsMarker)
        #     self.finish()
        #     self.request.response.redirect(self.request["ACTUAL_URL"])
        # else:
        #     with tempfile.TemporaryFile(mode="w+") as f:
        #         self.start()
        #         for number, datum in enumerate(content_generator, start=1):
        #             if number == 1:
        #                 f.write("[")
        #             else:
        #                 f.write(",")
        #             json.dump(datum, f, sort_keys=True, indent=4)
        #         if number:
        #             if  self.errors and self.write_errors:
        #                 f.write(",")
        #                 errors = {"unexported_paths": self.errors}
        #                 json.dump(errors, f, indent=4)
        #             f.write("]")
        #         msg = _(u"Exported {} {}").format(number, self.portal_type)
        #         logger.info(msg)
        #         api.portal.show_message(msg, self.request)
        #         response = self.request.response
        #         response.setHeader("content-type", "application/json")
        #         response.setHeader("content-length", f.tell())
        #         response.setHeader(
        #             "content-disposition",
        #             'attachment; filename="{0}"'.format(filename),
        #         )
        #         if self.include_blobs == 1:
        #             # remove marker interface
        #             noLongerProvides(self.request, IBase64BlobsMarker)
        #         elif self.include_blobs == 2:
        #             noLongerProvides(self.request, IPathBlobsMarker)
        #         f.seek(0)
        #         self.finish()
        #         return response.write(safe_bytes(f.read()))

    def update_query(self, query):
        return query

    def update(self):
        self.portal_type = self.portal_type or TYPES_TO_EXPORT

    def global_obj_hook(self, obj):
        """Used this to inspect the content item before serialisation data.
        Bad: Changing the content-item is a bad idea.
        Good: Return None if you want to skip this particular object.
        """
        return obj

    def global_dict_hook(self, item, obj):
        """Used this to modify the serialized data.
        Return None if you want to skip this particular object.
        """
        if obj.portal_type in [
            "genweb.tfemarket.market", "genweb.tfemarket.offer",
                "genweb.tfemarket.application"]:
            item.update({u'creators': [it for it in obj.creators]})
            item.update({u'contributors': [it for it in obj.contributors]})
            item.update({u'expires': obj.expires().strftime(
                '%Y-%m-%dT%H:%M:%S+00:00' if obj.expires else None)})
            item.update({u'exclude_from_nav': obj.exclude_from_nav})

        if obj.portal_type == "genweb.tfemarket.offer":
            if item['offer_type'] == 'Projecte':
                item['offer_type'] = u'Project'

        if obj.portal_type == "genweb.ens.ens":
            if item['institution_type'] == None:
                item['institution_type'] = '-'

        item = self.export_annotations(item, obj)
        return item

    def export_annotations(self, item, obj):
        results = {}
        annotations = IAnnotations(obj)
        for key in ANNOTATIONS_TO_EXPORT:
            data = annotations.get(key)
            if data:
                # Lo comento lo del IJsonCompatible porque sino
                # i18n_message_converter plone.restapi.serializer.converter.py lo traduce y no funciona
                # results[key] = IJsonCompatible(data, None)
                results[key] = data
        if results:
            item[ANNOTATIONS_KEY] = results
        return item

    # def export_revisions(self, item, obj):
    #     if not self.include_revisions:
    #         return item
    #     try:
    #         repo_tool = api.portal.get_tool("portal_repository")
    #         history_metadata = repo_tool.getHistoryMetadata(obj)
    #         serializer = getMultiAdapter((obj, self.request), ISerializeToJson)
    #         content_history_viewlet = ContentHistoryViewlet(obj, self.request, None, None)
    #         content_history_viewlet.navigation_root_url = ""
    #         content_history_viewlet.site_url = ""
    #         full_history = content_history_viewlet.fullHistory() or []
    #         history = [i for i in full_history if i["type"] == "versioning"]
    #         if not history or len(history) == 1:
    #             return item
    #         item["exportimport.versions"] = {}
    #         # don't export the current version again
    #         for history_item in history[1:]:
    #             version_id = history_item["version_id"]
    #             item_version = serializer(include_items=False, version=version_id)
    #             item_version = self.update_data_for_migration(item_version, obj)
    #             item["exportimport.versions"][version_id] = item_version
    #             # inject metadata (missing for Archetypes content):
    #             comment = history_metadata.retrieve(version_id)["metadata"]["sys_metadata"]["comment"]
    #             if comment and comment != item["exportimport.versions"][version_id].get("changeNote"):
    #                 item["exportimport.versions"][version_id]["changeNote"] = comment
    #         # current changenote
    #         item["changeNote"] = history_metadata.retrieve(-1)["metadata"]["sys_metadata"]["comment"]
    #         return item
    #     except:
    #         return item
