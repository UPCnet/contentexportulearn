# -*- coding: UTF-8 -*-
import logging

from collective.exportimport.export_other import BaseExport
from plone import api
from plone.restapi.serializer.converters import json_compatible
import json


logger = logging.getLogger(__name__)

class ExportPortalRoleManager(BaseExport):
    """Export various settings for haiku sites
    """

    def __call__(self, download_to_server=False):
        self.title = "Export portal role manager"
        self.download_to_server = download_to_server
        if not self.request.form.get("form.submitted", False):
            return self.index()

        data = self.export_portalrolemanager()
        self.download(data)

    def export_portalrolemanager(self):
        portal = api.portal.get()
        role_manager = portal.acl_users.portal_role_manager
        roles = role_manager.enumerateRoles()

        results = {}
        result = []
        for role in roles:
            users_assigned = role_manager.listAssignedPrincipals(role['id'])
            try:
                info_role_manager = dict(role_id=role['id'],
                                         users_assigned=users_assigned
                                    )
                result.append(info_role_manager)
            except:
                logger.info('HA FALLAT LA INFO DE {}'.format(role['id']))
        results = result

        return results
      
