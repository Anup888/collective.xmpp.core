from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.app.testing import IntegrationTesting, FunctionalTesting
from plone.registry.interfaces import IRegistry
from twisted.words.protocols.jabber.jid import JID
from zope.component import getUtility
from zope.configuration import xmlconfig

from jarn.xmpp.twisted.interfaces import IZopeReactor
from jarn.xmpp.twisted.testing import REACTOR_FIXTURE, NO_REACTOR_FIXTURE
from jarn.xmpp.twisted.testing import wait_on_client_deferreds
from jarn.xmpp.twisted.testing import wait_for_client_state

from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.subscribers.startup import setupAdminClient
from collective.xmpp.core.utils.setup import _setupXMPPEnvironment


class XMPPCoreNoReactorFixture(PloneSandboxLayer):

    defaultBases = (NO_REACTOR_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import jarn.jsi18n
        import collective.xmpp.core
        xmlconfig.file('configure.zcml', jarn.jsi18n,
                       context=configurationContext)

        xmlconfig.file('configure.zcml', collective.xmpp.core,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, 'collective.xmpp.core:default')
        registry = getUtility(IRegistry)
        registry['collective.xmpp.adminJID'] = 'admin@localhost'
        registry['collective.xmpp.pubsubJID'] = 'pubsub.localhost'
        registry['collective.xmpp.conferenceJID'] = 'conference.localhost'
        registry['collective.xmpp.xmppDomain'] = 'localhost'


XMPPCORE_NO_REACTOR_FIXTURE = XMPPCoreNoReactorFixture()

XMPPCORE_NO_REACTOR_INTEGRATION_TESTING = IntegrationTesting(
    bases=(XMPPCORE_NO_REACTOR_FIXTURE, ),
    name="XMPPCoreNoReactorFixture:Integration")
XMPPCORE_NO_REACTOR_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(XMPPCORE_NO_REACTOR_FIXTURE, ),
    name="XMPPCoreNoReactorFixture:Functional")


def _doNotUnregisterOnDisconnect(event):
    pass


class XMPPCoreFixture(PloneSandboxLayer):

    defaultBases = (REACTOR_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import jarn.jsi18n
        import collective.xmpp.core
        xmlconfig.file('configure.zcml', jarn.jsi18n,
                       context=configurationContext)

        # Normally on a client disconnect we unregister the AdminClient
        # utility. We can't do that here as we need to disconnect the
        # client and clean up to keep twisted happy.
        collective.xmpp.core.subscribers.startup.adminDisconnected = \
            _doNotUnregisterOnDisconnect

        xmlconfig.file('configure.zcml', collective.xmpp.core,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, 'collective.xmpp.core:default')
        registry = getUtility(IRegistry)
        registry['collective.xmpp.adminJID'] = 'admin@localhost'
        registry['collective.xmpp.pubsubJID'] = 'pubsub.localhost'
        registry['collective.xmpp.conferenceJID'] = 'conference.localhost'
        registry['collective.xmpp.xmppDomain'] = 'localhost'
        setupAdminClient(None, None)
        client = getUtility(IAdminClient)
        wait_for_client_state(client, 'authenticated')

    def testSetUp(self):
        client = getUtility(IAdminClient)
        if client._state == 'disconnected':
            zr = getUtility(IZopeReactor)
            zr.reactor.callFromThread(client.connect)

        wait_for_client_state(client, 'authenticated')
        _setupXMPPEnvironment(client,
            member_jids=[JID('test_user_1_@localhost')],
            member_passwords={JID('test_user_1_@localhost'): 'secret'})
        wait_on_client_deferreds(client)

    def testTearDown(self):
        client = getUtility(IAdminClient)
        client.disconnect()
        wait_for_client_state(client, 'disconnected')


XMPPCORE_FIXTURE = XMPPCoreFixture()

XMPPCORE_INTEGRATION_TESTING = IntegrationTesting(bases=(XMPPCORE_FIXTURE, ),
    name="XMPPCoreFixture:Integration")
XMPPCORE_FUNCTIONAL_TESTING = FunctionalTesting(bases=(XMPPCORE_FIXTURE, ),
    name="XMPPCoreFixture:Functional")