# -*- coding: UTF-8 -*-
from Acquisition import aq_base
from collective.exportimport.export_content import ExportContent
from collective.exportimport.export_content import fix_portal_type
from collective.exportimport.export_content import safe_bytes
from collective.exportimport.interfaces import IRawRichTextMarker
from zope.annotation.interfaces import IAnnotations

from App.config import getConfiguration
from collective.exportimport import _
from collective.exportimport import config
from collective.exportimport.interfaces import IBase64BlobsMarker
from collective.exportimport.interfaces import IMigrationMarker
from collective.exportimport.interfaces import IPathBlobsMarker
from operator import itemgetter
from plone import api
from plone.app.layout.viewlets.content import ContentHistoryViewlet
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.serializer.converters import json_compatible
from plone.restapi.serializer.dxcontent import SerializeFolderToJson
from plone.restapi.serializer.dxcontent import SerializeToJson
from plone.uuid.interfaces import IUUID
from DateTime.DateTime import DateTime
from zope.interface import providedBy
from Products.CMFPlone.interfaces import IPloneSiteRoot
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

logger = logging.getLogger(__name__)

COLLECTION_METADATA_FIELDS = (
    "query",
    "sort_on",
    "sort_reversed",
    "item_count",
    "customViewFields",
    "limit",
    "batch_size",
    "title",
    "description",
)


# CMF methods shadowed as plain values by migration4to5 on communities.
MIGRATION_SHADOWED_METHODS = ("created", "modified", "UID", "Creator")


def _shadowed_instance_value(obj, name):
    value = obj.__dict__.get(name)
    if value is not None and not callable(value):
        return value
    return None


class _ExportMigrationProxy(object):
    """Read-only export wrapper for migration4to5 artifacts on communities.

    migration4to5 sets created/UID/Creator as instance attributes, shadowing
    CMF methods. A transparent proxy cannot fix that; methods must be defined
    explicitly on this class.
    """

    def __init__(self, obj):
        self._obj = obj

    def created(self):
        shadowed = _shadowed_instance_value(self._obj, "created")
        if shadowed is not None:
            return DateTime(shadowed)
        creation_date = getattr(self._obj, "CreationDate", None)
        if creation_date:
            return DateTime(creation_date)
        return self._obj.created()

    def modified(self):
        shadowed = _shadowed_instance_value(self._obj, "modified")
        if shadowed is not None:
            return DateTime(shadowed)
        modification_date = getattr(self._obj, "ModificationDate", None)
        if modification_date:
            return DateTime(modification_date)
        return self._obj.modified()

    def UID(self):
        shadowed = _shadowed_instance_value(self._obj, "UID")
        if shadowed is not None:
            return shadowed
        return self._obj.UID()

    def Creator(self):
        shadowed = _shadowed_instance_value(self._obj, "Creator")
        if shadowed is not None:
            return shadowed
        return self._obj.Creator()

    def __providedBy__(self):
        return providedBy(self._obj)

    def __getattr__(self, name):
        return getattr(self._obj, name)


def _needs_migration_fixup(obj):
    if obj.portal_type != "ulearn.community":
        return False
    for name in MIGRATION_SHADOWED_METHODS:
        if _shadowed_instance_value(obj, name) is not None:
            return True
    return False


def _serialize_legacy_collection(obj, request):
    """Export Collection metadata without calling results()."""
    item = SerializeToJson(obj, request)()
    for name in COLLECTION_METADATA_FIELDS:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                item[name] = json_compatible(value)
    item.setdefault("items", [])
    item["items_total"] = 0
    return item

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
    "ulearn.community",
    "ulearn.banner",
    "ulearn.video",
    "ulearn.video_embed",
    "BannerContainer",
    "BannerItem",
    "LIF",
    "LRF",
    "Logos_Container",
    "Logos_Footer",
    "privateFolder",
    "AppFile",
    "AppImage",
    "Interaccio",
    "ulearn.abacus.location",
    "ulearn.abacus.ubication",
    "ulearn.abacus.area",
    "ulearn.abacus.work_placement",
    "ulearn.affiliate",
]

PATH = ''

# Content for test-migrations
PATHS_TO_EXPORT = []

MARKER_INTERFACES_TO_EXPORT = []

ANNOTATIONS_TO_EXPORT = [
    "portlets.col.ContentWellPortlets.AbovePortletManager1",
    "portlets.col.ContentWellPortlets.AbovePortletManager2",
    "portlets.col.ContentWellPortlets.AbovePortletManager3",
    "portlets.col.ContentWellPortlets.BelowPortletManager1",
    "portlets.col.ContentWellPortlets.BelowPortletManager2",
    "portlets.col.ContentWellPortlets.BelowPortletManager3",
    "portlets.col.ContentWellPortlets.BelowTitlePortletManager1",
    "portlets.col.ContentWellPortlets.BelowTitlePortletManager2",
    "portlets.col.ContentWellPortlets.BelowTitlePortletManager3",
    "base5.core.flash",
    "base5.core.important",
    "base5.core.outoflist",
    "base5.core.show_new_in_app",
    "ulearn5.msteams",
    "ulearn5.nomines",
    "ulearn5.nominesmedichem",
    "ulearn5.zoom",
]

ANNOTATIONS_KEY = "exportimport.annotations"

MARKER_INTERFACES_KEY = "exportimport.marker_interfaces"


class CustomExportContent(ExportContent):

    QUERY = {
    }

    DROP_PATHS = [
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

    def serialize_object(self, obj):
        if _needs_migration_fixup(obj):
            proxy = _ExportMigrationProxy(obj)
            return SerializeFolderToJson(proxy, self.request)(
                include_items=False
            )

        serializer = getMultiAdapter((obj, self.request), ISerializeToJson)
        if IPloneSiteRoot.providedBy(obj):
            return serializer()
        if getattr(aq_base(obj), "isPrincipiaFolderish", False):
            return serializer(include_items=False)
        try:
            return serializer()
        except TypeError:
            if obj.portal_type not in ("Collection", "Topic"):
                raise
            logger.warning(
                "Legacy collection export fallback for %s",
                obj.absolute_url(),
            )
            return _serialize_legacy_collection(obj, self.request)

    def export_content(self):
        query = self.build_query()
        catalog = api.portal.get_tool("portal_catalog")
        brains = catalog.unrestrictedSearchResults(**query)
        logger.info(u"Exporting {} {}".format(len(brains), self.portal_type))

        alsoProvides(self.request, IRawRichTextMarker)

        for index, brain in enumerate(brains, start=1):
            skip = False
            if brain.UID in self.DROP_UIDS:
                continue

            for drop in self.DROP_PATHS:
                if drop in brain.getPath():
                    skip = True

            if skip:
                continue

            if not index % 100:
                logger.info(u"Handled {} items...".format(index))
            try:
                obj = brain.getObject()
            except Exception:
                msg = u"Error getting brain {}".format(brain.getPath())
                self.errors.append({'path': None, 'message': msg})
                logger.exception(msg, exc_info=True)
                continue
            if obj is None:
                msg = u"brain.getObject() is None {}".format(brain.getPath())
                logger.error(msg)
                self.errors.append({'path': None, 'message': msg})
                continue
            obj = self.global_obj_hook(obj)
            if not obj:
                continue
            try:
                self.safe_portal_type = fix_portal_type(obj.portal_type)
                item = self.serialize_object(obj)
                item = self.update_export_data(item, obj)
                yield item
            except Exception:
                msg = u"Error exporting {}".format(obj.absolute_url())
                self.errors.append({'path': obj.absolute_url(), 'message': msg})
                logger.exception(msg, exc_info=True)

    def global_dict_hook(self, item, obj):
        """Used this to modify the serialized data.
        Return None if you want to skip this particular object.
        """
        if obj.portal_type == "ulearn.community":
            adapter = obj.adapted()
            acl = adapter.get_acl()
            item.update({'acl': acl})
            creators = obj.creators
            item.update({'creators': creators})

        item = self.export_annotations(item, obj)
        return item

    def export_annotations(self, item, obj):
        results = {}
        try:
           annotations = IAnnotations(obj)
        except TypeError:
           annotations = None

        if annotations:

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
