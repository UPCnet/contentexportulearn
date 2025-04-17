# -*- coding: UTF-8 -*-
import logging

from collective.exportimport.export_other import BaseExport
from plone import api
from plone.restapi.serializer.converters import json_compatible
from zope.component import getUtility
from plone.registry.interfaces import IRegistry

from genweb.controlpanel.interface import IGenwebControlPanelSettings

from plone.formwidget.recaptcha.interfaces import IReCaptchaSettings

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
            if product["id"].startswith("genweb."):
                addons.append(product["id"])
        results["addons"] = addons

        portal = api.portal.get()

        image_capcalera_url = portal.absolute_url() + '/portal_skins/custom/capcalera.jpg'
        imgData = requests.get(image_capcalera_url).content
        b64data_image_capcalera = str(base64.b64encode(imgData).decode('utf-8'))
        controlpanel = {}

        # genweb-controlpanel
        gwsettings = getUtility(IRegistry).forInterface(IGenwebControlPanelSettings)
        controlpanel["genweb6.core.controlpanels.footer.IFooterSettings"] = dict(
            signatura_ca=gwsettings.signatura_unitat_ca,
            signatura_es=gwsettings.signatura_unitat_es,
            signatura_en=gwsettings.signatura_unitat_en)
        controlpanel["genweb6.core.controlpanels.header.IHeaderSettings"] = dict(
            main_hero_style='text-hero'
            if gwsettings.treu_imatge_capsalera else 'image-hero',
            content_hero_style='text-hero'
            if gwsettings.treu_imatge_capsalera else 'image-hero',
            html_title_ca=gwsettings.html_title_ca,
            html_title_es=gwsettings.html_title_es,
            html_title_en=gwsettings.html_title_en, hero_image=b64data_image_capcalera,
            treu_menu_horitzontal=gwsettings.treu_menu_horitzontal,
            amaga_identificacio=gwsettings.amaga_identificacio,
            idiomes_publicats=gwsettings.idiomes_publicats,
            languages_link_to_root=gwsettings.languages_link_to_root)
        controlpanel["genweb6.upc.controlpanels.upc.IUPCSettings"] = dict(
            contacte_al_peu=gwsettings.contacte_al_peu,
            contacte_id=gwsettings.contacte_id,
            contacte_BBDD_or_page=gwsettings.contacte_BBDD_or_page,
            contacte_multi_email=gwsettings.contacte_multi_email,
            contact_emails_table=gwsettings.contact_emails_table)
        # @@mail-controlpanel
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
        # @@recaptcha-settings
        recaptchasettings = getUtility(IRegistry).forInterface(IReCaptchaSettings)
        controlpanel["plone.formwidget.recaptcha.interfaces.IReCaptchaSettings"] = dict(
            center_code=recaptchasettings.public_key,
            private_key=recaptchasettings.private_key,
            display_theme=recaptchasettings.display_theme,
            display_type=recaptchasettings.display_type,
            display_size=recaptchasettings.display_size)
        # @@language-controlpanel
        default_language = api.portal.get_default_language()
        controlpanel["plone.app.multilingual"] = dict(default_language=default_language)

        if "genweb.tfemarket" in results["addons"]:
            from genweb.tfemarket.controlpanel import ITableTitulacions, ITfemarketSettings, IBUSSOASettings, IIdentitatDigitalSettings

            tfesettings = getUtility(IRegistry).forInterface(ITfemarketSettings)
            controlpanel["genweb6.tfemarket.controlpanels.tfemarket.ITfemarketSettings"] = dict(center_code=tfesettings.center_code,
                                                                                                center_name=tfesettings.center_name,
                                                                                                review_state=tfesettings.review_state,
                                                                                                enroll_type=tfesettings.enroll_type,
                                                                                                alternative_email=tfesettings.alternative_email,
                                                                                                alternative_email_name=tfesettings.alternative_email_name,
                                                                                                topics=tfesettings.topics,
                                                                                                tags=tfesettings.tags,
                                                                                                languages=tfesettings.languages,
                                                                                                titulacions_table=tfesettings.titulacions_table,
                                                                                                life_period=tfesettings.life_period,
                                                                                                view_num_students=tfesettings.view_num_students,
                                                                                                import_offers=tfesettings.import_offers,
                                                                                                count_offers=tfesettings.count_offers)
            bussoasettings = getUtility(IRegistry).forInterface(IBUSSOASettings)
            controlpanel["genweb6.upc.controlpanels.bus_soa.IBusSOASettings"] = dict(
                bus_url=bussoasettings.bus_url, bus_user=bussoasettings.bus_user,
                bus_password=bussoasettings.bus_password,
                bus_apikey=bussoasettings.bus_apikey)

            identitatdigitalsettings = getUtility(
                IRegistry).forInterface(IIdentitatDigitalSettings)
            controlpanel["genweb6.upc.controlpanels.identitat_digital.IIdentitatDigitalSettings"] = dict(
                identitat_url=identitatdigitalsettings.identitat_url, identitat_apikey=identitatdigitalsettings.identitat_apikey)

        if "genweb.serveistic" in results["addons"]:
            from genweb.serveistic.controlpanel import IServeisTICFacetesControlPanelSettings, IServeisTICControlPanelSettings

            serveisticsettings = getUtility(IRegistry).forInterface(
                IServeisTICControlPanelSettings)
            controlpanel["genweb6.serveistic.controlpanels.serveistic.IServeisTICControlPanelSettings"] = dict(url_info_serveistic=serveisticsettings.url_info_serveistic,
                                                                                                               show_filters=serveisticsettings.show_filters,
                                                                                                               ws_problemes_endpoint=serveisticsettings.ws_problemes_endpoint,
                                                                                                               ws_problemes_login_username=serveisticsettings.ws_problemes_login_username,
                                                                                                               ws_problemes_login_password=serveisticsettings.ws_problemes_login_password,
                                                                                                               ws_indicadors_service_id=serveisticsettings.ws_indicadors_service_id,
                                                                                                               ws_indicadors_endpoint=serveisticsettings.ws_indicadors_endpoint,
                                                                                                               ws_indicadors_key=serveisticsettings.ws_indicadors_key,
                                                                                                               update_indicadors_passphrase=serveisticsettings.update_indicadors_passphrase,
                                                                                                               ga_key_json=serveisticsettings.ga_key_json,
                                                                                                               ga_view_id=serveisticsettings.ga_view_id)
            facetessettings = getUtility(IRegistry).forInterface(
                IServeisTICFacetesControlPanelSettings)
            controlpanel["genweb6.serveistic.controlpanels.facetes.IServeisTICFacetesControlPanelSettings"] = dict(
                facetes_table=facetessettings.facetes_table)

        results["controlpanel"] = json_compatible(controlpanel)
        return results
