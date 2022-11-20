# TsuserverDR, a Danganronpa Online server based on tsuserver3, an Attorney Online server
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
# Current project leader: 2018-22 Chrezm/Iuvee <thechrezm@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import datetime
import logging
import sys
import time
import traceback
import typing

from typing import Union

from server.constants import Constants

if typing.TYPE_CHECKING:
    from server.client_manager import ClientManager
    from server.tsuserver import TsuserverDR

def setup_logger(debug):
    logging.Formatter.converter = time.gmtime
    debug_formatter = logging.Formatter('[%(asctime)s UTC]%(message)s')
    srv_formatter = logging.Formatter('[%(asctime)s UTC]%(message)s')

    debug_log = logging.getLogger('debug')
    debug_log.setLevel(logging.DEBUG)

    debug_handler = logging.FileHandler('logs/debug.log', encoding='utf-8')
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(debug_formatter)
    debug_log.addHandler(debug_handler)

    if not debug:
        debug_log.disabled = True

    server_log = logging.getLogger('server')
    server_log.setLevel(logging.INFO)

    current_month = "{:02d}".format(datetime.date.today().month)
    logfile_name = 'logs/server-{}-{}.log'.format(datetime.date.today().year, current_month)
    server_handler = logging.FileHandler(logfile_name, encoding='utf-8')
    server_handler.setLevel(logging.INFO)
    server_handler.setFormatter(srv_formatter)
    server_log.addHandler(server_handler)

#    rp_log = logging.getLogger('rp')
#    rp_log.setLevel(logging.INFO)

#    rp_handler = logging.FileHandler('logs/rp.log', encoding='utf-8')
#    rp_handler.setLevel(logging.INFO)
#    rp_handler.setFormatter(rp_formatter)
#    rp_log.addHandler(rp_handler)

    error_log = logging.getLogger('error')
    error_log.setLevel(logging.ERROR)

    return (debug_log, debug_handler), (server_log, server_handler)


def log_debug(msg: str, client: Union[ClientManager.Client, None] = None):
    msg = parse_client_info(client) + msg
    logging.getLogger('debug').debug(msg)


def _print_exception(etype, evalue, etraceback):
    return f'\n{"".join(traceback.format_exception(etype, evalue, etraceback))}'

def _log_error(server: TsuserverDR) -> str:
    msg = ''

    # Add list of most recent packets
    msg += f'\n\n\n= {server.logged_packet_limit} most recent packets dump ='
    if not server.logged_packets:
        msg += '\nNo logged packets.'
    else:
        for logged_packet in server.logged_packets:
            str_logged_packet = ' '.join(logged_packet)
            msg += f'\n{str_logged_packet}'

    # Add list of clients to error log
    try:
        msg += '\n\n\n= Dump of clients ='
        msg += f'\n*Number of clients: {len(server.get_clients())}'
        msg += '\n*Current clients'
        clients = sorted(server.get_clients(), key=lambda c: c.id)

        for c in clients:
            try:
                msg += f'\n\n{c.get_info(as_mod=True)}'
            except Exception:
                etype, evalue, etraceback = sys.exc_info()
                msg += f'\n\nError generating dump of client {c.id}.'
                msg += _print_exception(etype, evalue, etraceback)
    except Exception:
        etype, evalue, etraceback = sys.exc_info()
        msg += '\nError generating dump of clients.'
        msg += _print_exception(etype, evalue, etraceback)


    # Add list of hubs to error log
    try:
        msg += '\n\n\n= Dump of hubs ='
        msg += f'\n*Number of hubs: {len(server.hub_manager.get_managees())}'
        msg += '\n*Current hubs'
        hubs = sorted(server.hub_manager.get_managees(),
                      key=lambda hub: hub.get_id())

        for hub in hubs:
            msg += f'\n\n== Hub {hub.get_id()} =='

            try:
                msg += '\n=== Area list ==='
                try:
                    msg += f'\n*Current area list: {hub.area_manager.get_source_file()}'
                    msg += f'\n*Previous area list: {hub.area_manager.get_previous_source_file()}'
                    msg += '\n*Current areas:'

                    for area in hub.area_manager.get_areas():
                        msg += f'\n**{area}'
                        for c in area.clients:
                            msg += f'\n***{c}'
                except Exception:
                    etype, evalue, etraceback = sys.exc_info()
                    msg += f'\nError generating dump of areas for hub {hub.get_id()}.'
                    msg += _print_exception(etype, evalue, etraceback)

            except Exception:
                etype, evalue, etraceback = sys.exc_info()
                msg += f'\nError generating dump of hub {hub.get_id()}.'
                msg += _print_exception(etype, evalue, etraceback)


    except Exception:
        etype, evalue, etraceback = sys.exc_info()
        msg += '\nError generating dump of hubs.'
        msg += _print_exception(etype, evalue, etraceback)

    return msg

def log_error(msg: str, server: Union[TsuserverDR, None], errortype='P') -> str:
    # errortype "C" if server raised an error as a result of a client packet.
    # errortype "D" if player manually requested an error dump
    # errortype "P" if server raised an error for any other reason
    error_log = logging.getLogger('error')

    file = f'logs/{Constants.get_time_iso()}{errortype}.log'
    file = file.replace(':', '')
    error_handler = logging.FileHandler(file, encoding='utf-8')

    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter('[%(asctime)s UTC]%(message)s'))
    error_log.addHandler(error_handler)

    if server:
        msg += _log_error(server)
    else:
        # Case server was not initialized properly, so areas and clients are not set
        msg += ('\nServer was not initialized, so packet, client and area dumps could not be '
                'generated.')

    # Write and log
    error_log.error(msg)
    error_log.removeHandler(error_handler)

    log_pserver('Successfully created server dump file {}'.format(file))
    return file


def log_server(msg, client=None):
    msg = f'{parse_client_info(client)}{msg}'
    logging.getLogger('server').info(msg)


def log_print(msg, client=None):
    msg = f'{parse_client_info(client)}{msg}'
    current_time = Constants.get_time_iso()
    print('{}: {}'.format(current_time, msg))


def log_pdebug(msg, client=None):
    log_debug(msg, client=client)
    log_print(msg, client=client)


def log_pserver(msg, client=None):
    log_server(msg, client=client)
    log_print(msg, client=client)


def parse_client_info(client):
    if client is None:
        return ''
    hdid = client.get_hdid()
    ipid = client.get_ip()
    if ipid is None:
        info = None
    else:
        info = '{:<15}'.format(ipid)
    if client.is_mod:
        return '[{}][{}][{}][MOD]'.format(info, hdid, client.id)
    return '[{}][{}][{}]'.format(info, hdid, client.id)
