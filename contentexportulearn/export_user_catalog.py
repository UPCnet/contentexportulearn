# -*- coding: UTF-8 -*-
import logging

from base5.core.utils import get_all_user_properties
from collective.exportimport.export_other import BaseExport
from plone import api
from plone.restapi.serializer.converters import json_compatible
from souper.soup import get_soup
from zope.component import getMultiAdapter

from itertools import chain

logger = logging.getLogger(__name__)


class ExportUserCatalog(BaseExport):
    """Export user directory data for uShare6 migration (``export_user_catalog.json``)."""

    def __call__(self, download_to_server=False):
        self.title = "Export user catalog (user_properties)"
        self.download_to_server = download_to_server
        if not self.request.form.get("form.submitted", False):
            return self.index()

        data = self.export_user_catalog()
        self.download(data)

    def export_user_catalog(self):
        """Same shape as ``GET /api/userspropertiesmigrationsoup``."""
        portal = api.portal.get()
        soup = get_soup("user_properties", portal)
        result = []
        for record in soup.data.values():
            userid = str(record.attrs.get("id", "") or "")
            if not userid:
                continue
            user = api.user.get(username=userid)
            if not user:
                continue
            try:
                properties = get_all_user_properties(user)
                result.append(
                    json_compatible(
                        {"id": user.id, "properties": properties}
                    )
                )
            except Exception:
                logger.exception(
                    "Failed exporting user catalog entry for %s", userid
                )

        if result:
            return result

        # Empty soup: fall back to LDAP enumeration (``userspropertiesmigration``).
        logger.info(
            "user_properties soup empty — exporting via pas_search (LDAP)"
        )
        search_view = getMultiAdapter(
            (portal, self.request), name="pas_search"
        )
        ldap_users = search_view.merge(
            chain(
                *[
                    search_view.searchUsers(**{field: ""})
                    for field in ["name"]
                ]
            ),
            "userid",
        )
        for ldap_user in ldap_users:
            user = api.user.get(username=ldap_user["id"])
            if not user:
                continue
            try:
                properties = get_all_user_properties(user)
                result.append(
                    json_compatible(
                        {"id": user.id, "properties": properties}
                    )
                )
            except Exception:
                logger.exception(
                    "Failed exporting LDAP user properties for %s",
                    ldap_user["id"],
                )
        return result
