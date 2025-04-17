# -*- coding: UTF-8 -*-
import logging

from collective.exportimport.export_other import BaseExport
from plone import api
from plone.restapi.serializer.converters import json_compatible
from zope.component import getUtility
from plone.registry.interfaces import IRegistry

from base5.core.controlpanel.core import IBaseCoreControlPanelSettings
from mrs5.max.browser.controlpanel import IMAXUISettings
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.controlpopup import IPopupSettings
from ulearn5.core.controlportlets import IPortletsSettings


import base64
import requests

logger = logging.getLogger(__name__)


class ExportControlpanels(BaseExport):
    """Export various controlpanels
    """

    def __call__(self, download_to_server=False):
        self.title = "Export installed addons various settings"
        self.download_to_server = download_to_server
        if not self.request.form.get("form.submitted", False):
            return self.index()

        data = self.export_cotrolpanels()
        self.download(data)

    def export_cotrolpanels(self):
        results = {}
        addons = []
        qi = api.portal.get_tool("portal_quickinstaller")
        for product in qi.listInstalledProducts():
            if product["id"].startswith(("ulearn5.", "mrs5.", "base5.")):
                addons.append(product["id"])
        results["addons"] = addons

        portal = api.portal.get()

        # image_capcalera_url = portal.absolute_url() + '/portal_skins/custom/capcalera.jpg'
        # imgData = requests.get(image_capcalera_url).content
        # b64data_image_capcalera = str(base64.b64encode(imgData).decode('utf-8'))
        controlpanel = {}

        # Base settings-controlpanel
        base_settings = getUtility(IRegistry).forInterface(
            IBaseCoreControlPanelSettings)
        controlpanel["base5.core.controlpanel.IBaseCoreControlPanelSettings"] = dict(
            user_properties_extender=base_settings.user_properties_extender,
            custom_editor_icons=base_settings.custom_editor_icons,
            elasticsearch=base_settings.elasticsearch,
            alt_ldap_uri=base_settings.alt_ldap_uri,
            alt_bind_dn=base_settings.alt_bind_dn,
            alt_bindpasswd=base_settings.alt_bindpasswd,
            alt_base_dn=base_settings.alt_base_dn,
            groups_query=base_settings.groups_query,
            user_groups_query=base_settings.user_groups_query,
            create_group_type=base_settings.create_group_type)
        # MAX UI settings-controlpanel
        maxui_settings = getUtility(IRegistry).forInterface(IMAXUISettings)
        controlpanel["mrs5.max.controlpanel.IMAXUISettings"] = dict(
            max_server=maxui_settings.max_server,
            oauth_server=maxui_settings.oauth_server,
            max_server_alias=maxui_settings.max_server_alias,
            max_restricted_username=maxui_settings.max_restricted_username,
            max_restricted_token=maxui_settings.max_restricted_token,
            hub_server=maxui_settings.hub_server,
            domain=maxui_settings.domain)
        # Ulearn settings-controlpanel
        ulearn_settings = getUtility(IRegistry).forInterface(
            IUlearnControlPanelSettings)
        controlpanel["ulearn5.core.controlpanel.IUlearnControlPanelSettings"] = dict(
            html_title_ca=ulearn_settings.html_title_ca,
            html_title_es=ulearn_settings.html_title_es,
            html_title_en=ulearn_settings.html_title_en,
            campus_url=ulearn_settings.campus_url,
            library_url=ulearn_settings.library_url,
            threshold_winwin1=ulearn_settings.threshold_winwin1,
            threshold_winwin2=ulearn_settings.threshold_winwin2,
            threshold_winwin3=ulearn_settings.threshold_winwin3,
            stats_button=ulearn_settings.stats_button,
            info_servei=ulearn_settings.info_servei,
            activate_news=ulearn_settings.activate_news,
            activate_sharedwithme=ulearn_settings.activate_sharedwithme,
            buttonbar_selected=ulearn_settings.buttonbar_selected,
            cron_tasks=ulearn_settings.cron_tasks,
            url_private_policy=ulearn_settings.url_private_policy,
            url_site=ulearn_settings.url_site,
            main_color=ulearn_settings.main_color,
            secondary_color=ulearn_settings.secondary_color,
            maxui_form_bg=ulearn_settings.maxui_form_bg,
            alt_gradient_start_color=ulearn_settings.alt_gradient_start_color,
            alt_gradient_end_color=ulearn_settings.alt_gradient_end_color,
            background_property=ulearn_settings.background_property,
            background_color=ulearn_settings.background_color,
            buttons_color_primary=ulearn_settings.buttons_color_primary,
            buttons_color_secondary=ulearn_settings.buttons_color_secondary,
            color_community_organizative=ulearn_settings.color_community_organizative,
            color_community_open=ulearn_settings.color_community_open,
            color_community_closed=ulearn_settings.color_community_closed,
            nonvisibles=ulearn_settings.nonvisibles,
            people_literal=ulearn_settings.people_literal,
            quicklinks_literal=ulearn_settings.quicklinks_literal,
            quicklinks_icon=ulearn_settings.quicklinks_icon,
            quicklinks_table=ulearn_settings.quicklinks_table,
            activity_view=ulearn_settings.activity_view,
            language=ulearn_settings.language,
            url_forget_password=ulearn_settings.url_forget_password,
            show_news_in_app=ulearn_settings.show_news_in_app,
            show_literals=ulearn_settings.show_literals,
            url_terms=ulearn_settings.url_terms,
            subject_template=ulearn_settings.subject_template,
            message_template=ulearn_settings.message_template,
            message_template_activity_comment=ulearn_settings.message_template_activity_comment,
            types_notify_mail=ulearn_settings.types_notify_mail,
            gAnalytics_enabled=ulearn_settings.gAnalytics_enabled,
            gAnalytics_view_ID=ulearn_settings.gAnalytics_view_ID,
            gAnalytics_JSON_info=ulearn_settings.gAnalytics_JSON_info,
            bitly_username=ulearn_settings.bitly_username,
            bitly_api_key=ulearn_settings.bitly_api_key)
        # Popup-controlpanel
        popup_settings = getUtility(IRegistry).forInterface(IPopupSettings)
        controlpanel["ulearn5.core.controlpopup.IPopupSettings"] = dict(
            activate_notify=popup_settings.activate_notify,
            message_notify=popup_settings.message_notify,
            reload_notify=popup_settings.reload_notify,
            warning_birthday=popup_settings.warning_birthday,
            activate_birthday=popup_settings.activate_birthday,
            message_birthday=popup_settings.message_birthday)
        # Portlets-controlpanel
        portlets_settings = getUtility(IRegistry).forInterface(IPortletsSettings)
        controlpanel["ulearn5.core.controlportlets.IPortletsSettings"] = dict(
            portlets_Search=portlets_settings.portlets_Search,
            portlets_Review=portlets_settings.portlets_Review,
            portlets_Navigation=portlets_settings.portlets_Navigation,
            collective_polls_VotePortlet=portlets_settings.collective_polls_VotePortlet,
            plone_portlet_static_Static=portlets_settings.plone_portlet_static_Static,
            mrs5_max_maxui=portlets_settings.mrs5_max_maxui,
            mrs5_max_maxuichat=portlets_settings.mrs5_max_maxuichat,
            base_portlets_smart=portlets_settings.base_portlets_smart,
            ulearn_portlets_angularrouteview=portlets_settings.ulearn_portlets_angularrouteview,
            ulearn_portlets_buttonbar=portlets_settings.ulearn_portlets_buttonbar,
            ulearn_portlets_communities=portlets_settings.ulearn_portlets_communities,
            ulearn_portlets_profile=portlets_settings.ulearn_portlets_profile,
            ulearn_portlets_profilecommunity=portlets_settings.ulearn_portlets_profilecommunity,
            ulearn_portlets_thinnkers=portlets_settings.ulearn_portlets_thinnkers,
            ulearn_portlets_calendar=portlets_settings.ulearn_portlets_calendar,
            ulearn_portlets_mysubjects=portlets_settings.ulearn_portlets_mysubjects,
            ulearn_portlets_flashesinformativos=portlets_settings.ulearn_portlets_flashesinformativos,
            ulearn_portlets_importantnews=portlets_settings.ulearn_portlets_importantnews,
            ulearn_portlets_rss=portlets_settings.ulearn_portlets_rss,
            ulearn_portlets_discussion=portlets_settings.ulearn_portlets_discussion,
            ulearn_portlets_stats=portlets_settings.ulearn_portlets_stats,
            ulearn_portlets_recentchanges=portlets_settings.ulearn_portlets_recentchanges,
            ulearn_portlets_banners=portlets_settings.ulearn_portlets_banners,
            ulearn_portlets_quicklinks=portlets_settings.ulearn_portlets_quicklinks,
            ulearn_portlets_mycommunities=portlets_settings.ulearn_portlets_mycommunities)
        controlpanel["plone.app.controlpanel.mail.IMailSchema"] = dict(
            smtp_host=getattr(portal.MailHost, 'smtp_host', ''),
            smtp_port=int(getattr(portal.MailHost, 'smtp_port', 25)),
            smtp_userid=portal.MailHost.get('smtp_user_id'),
            smtp_pass=portal.MailHost.get('smtp_pass'),
            email_from_name=portal.getProperty('email_from_name', ''),
            email_from_address=portal.getProperty('email_from_address', ''),)
        # @@site-controlpanel
        portal_properties = api.portal.get_tool("portal_properties")
        site_props = portal_properties.site_properties
        controlpanel["plone.app.controlpanel.site.ISiteSchema"] = dict(
            site_title=portal.title, site_description=portal.description,
            exposeDCMetaTags=site_props.exposeDCMetaTags,
            display_pub_date_in_byline=site_props.displayPublicationDateInByline,
            enable_sitemap=site_props.enable_sitemap, webstats_js=site_props.
            webstats_js)

        results["controlpanel"] = json_compatible(controlpanel)
        return results
