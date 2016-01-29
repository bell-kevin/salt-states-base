# -*- coding: utf-8 -*-
'''
Salt returner that reports execution results back to sentry. The returner will
inspect the payload to identify errors and flag them as such.

Pillar needs something like:

.. code-block:: yaml

    raven:
      dsn: http://deadbeefdeadbeefdeadbeefdeadbeef:beefdeadbeefdeadbeefdeadbeefdead@sentry.example.com/1
      tags:
        - os
        - master
        - saltversion
        - cpuarch

and https://pypi.python.org/pypi/raven installed

The tags list (optional) specifies grains items that will be used as sentry
tags, allowing tagging of events in the sentry ui.
'''
from __future__ import absolute_import

# Import Python libs
import logging
import time

# Import Salt libs
import salt.utils.jid

try:
    from raven import Client
    has_raven = True
except ImportError:
    has_raven = False

logger = logging.getLogger(__name__)

# Define the module's virtual name
__virtualname__ = 'sentry'


def __virtual__():
    if not has_raven:
        return False
    return __virtualname__


def returner(ret):
    '''
    Log outcome to sentry. The returner tries to identify errors and report
    them as such. All other messages will be reported at info level.
    '''
    def connect_sentry(message, result):
        '''
        Connect to the Sentry server
        '''
        pillar_data = __salt__['pillar.raw']()
        grains = __salt__['grains.items']()
        sentry_data = {
            'result': result,
            'pillar': pillar_data,
            'grains': grains
        }
        data = {
            'platform': 'python',
            'culprit': ret['fun'],
            'level': 'error'
        }
        tags = {}
        if 'tags' in pillar_data['raven']:
            for tag in pillar_data['raven']['tags']:
                tags[tag] = grains[tag]

        if ret['return']:
            data['level'] = 'info'

        try:
            client = Client(dsn=pillar_data['raven']['dsn'],
                            raise_send_errors=True
                           )
        except KeyError as missing_key:
            logger.error(
                'Sentry returner need config \'{0}\' in pillar'.format(
                    missing_key
                )
            )
        else:
            try:
                client.capture(
                    'raven.events.Message',
                    message=message,
                    data=data,
                    extra=sentry_data,
                    tags=tags
                )
                time.sleep(3)
            except Exception as err:
                logger.error(
                    'Can\'t send message to sentry: {0}'.format(err),
                    exc_info=True
                )

    try:
        connect_sentry(ret['fun'], ret)
    except Exception as err:
        logger.error(
            'Can\'t run connect_sentry: {0}'.format(err),
            exc_info=True
        )


def prep_jid(nocache=False, passed_jid=None):  # pylint: disable=unused-argument
    '''
    Do any work necessary to prepare a JID, including sending a custom id
    '''
    return passed_jid if passed_jid is not None else salt.utils.jid.gen_jid()
