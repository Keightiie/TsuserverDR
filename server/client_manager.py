# TsuserverDR, server software for Danganronpa Online based on tsuserver3,
# which is server software for Attorney Online.
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
#           (C) 2018-22 Chrezm/Iuvee <thechrezm@gmail.com> (further additions)
#           (C) 2022 Tricky Leifa (further additions)
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
import json
import random
import string
import time
import typing
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

from server import client_changearea, clients, logger
from server.constants import Constants, FadeOption, TargetType
from server.exceptions import (AreaError, ClientError, HubError, PartyError,
                               TaskError, TrialError)
from server.hub_manager import _Hub
from server.music_manager import PersonalMusicManager
from server.subscriber import Publisher

if typing.TYPE_CHECKING:
    from asyncio.proactor_events import _ProactorSocketTransport

    # Avoid circular referencing
    from server.area_manager import AreaManager
    from server.network.ao_protocol import AOProtocol
    from server.tsuserver import TsuserverDR
    from server.zone_manager import ZoneManager


class ClientManager:
    class Client:
        def __init__(
            self,
            server: TsuserverDR,
            hub: _Hub,
            transport: _ProactorSocketTransport,
            user_id: int,
            ipid: int,
            protocol: AOProtocol = None
        ):
            self.server = server
            self.hub = hub
            self.transport = transport
            self.protocol = protocol
            self.area_changer = client_changearea.ClientChangeArea(self)
            # Needs to have length 2 to actually connect
            self.required_packets_received = set()
            self.can_askchaa = True  # Needs to be true to process an askchaa packet
            # AO version used established through ID pack
            self.version = ('Undefined', 'Undefined')
            self.packet_handler = clients.ClientDRO1d3d0()
            self.publisher = Publisher(self)

            self.disconnected = False
            self.hdid = ''
            self.ipid = ipid
            self.id = user_id
            self.char_id = None
            self.name = ''
            self.char_folder = ''
            self.char_showname = ''
            self.pos = 'wit'
            self.showname = ''
            self.joined = time.time()
            self.last_active = Constants.get_time()
            self.viewing_hubs = False

            self.ever_chose_character = False
            self.ever_outbounded_gamemode = False
            self.ever_outbounded_time_of_day = False

            self.music_manager = PersonalMusicManager(server, hub=None)
            # Avoid doing an OS call for a new client
            self.music_manager.transfer_contents_from_manager(
                self.server.hub_manager.get_default_managee().music_manager
            )

            self.area = hub.area_manager.default_area()
            self.new_area = self.area  # It is different from self.area in transition to a new area
            self.party = None
            self.is_mod = False
            self.is_gm = False
            self.is_dj = True
            self.is_cm = False
            self.is_muted = False
            self.is_ooc_muted = False
            self.pm_mute = False
            self.mod_call_time = 0
            self.evi_list = []
            self.muted_adverts = False
            self.muted_global = False
            self.pm_mute = False

            self.autopass = False
            self.disemvowel = False
            self.disemconsonant = False
            self.remove_h = False
            self.gimp = False
            self.is_visible = True
            self.multi_ic = None
            self.multi_ic_pre = ''
            self.following = None
            self.followedby = set()
            self.showname_history = list()
            self.is_transient = False
            self.old_handicap = None  # Use if custom handicap is overwritten with a server one
            self.is_movement_handicapped = False
            self.show_shownames = True
            self.is_bleeding = False
            self.get_foreign_rolls = False
            self.last_ic_message = ''
            self.last_ooc_message = ''
            self.first_person = False
            self.forward_sprites = True
            self.last_received_ic = (None, None, None)
            self.last_received_ic_notme = (None, None, None)
            self.is_blind = False
            self.is_deaf = False
            self.is_gagged = False
            self.send_deaf_space = False
            self.dicelog = list()
            self._zone_watched = None
            self.files = None
            self.get_nonautopass_autopass = False
            self.status = ''
            self.remembered_passages = dict()
            self.remembered_locked_passages = dict()
            self.remembered_statuses = dict()
            self.can_bypass_iclock = False
            self.char_log = list()
            self.ignored_players = set()
            self.paranoia = 2
            self.notecard = ''
            self.is_mindreader = False
            self.autoglance = False
            self.icon_visible = True

            # Sender stuff
            self.response_key = 'DEFAULT'

            # Pairing stuff
            self.charid_pair = -1
            self.pair_owner = False
            self.offset_pair = 0
            self.last_sprite = ''
            self.flip = 0
            self.claimed_folder = ''

            # Anti IC-flood-with-copy stuff
            # The last IC message they tried to send, without any
            self.last_ic_raw_message = None
            # modifications that it may have undergone afterwards (say, via gimp, gag, etc.)
            self.last_ic_char = ''  # The char they used to send their last IC message, not
            # necessarily equivalent to self.get_char_name()

            # music flood-guard stuff
            self.mute_time = 0
            self.mflood_interval = self.server.config['music_change_floodguard']['interval_length']
            self.mflood_times = self.server.config['music_change_floodguard']['times_per_interval']
            self.mflood_mutelength = self.server.config['music_change_floodguard']['mute_length']
            self.mflood_log = list()

        def generate_response_key(self):
            letters = string.ascii_lowercase
            self.response_key  = ''.join(random.choice(letters) for i in range(6))

        def send_command(self, command: str, *args: List):
            self.protocol.data_send(command, *args)

        def send_command_dict(self, command, dargs):
            _, to_send = self.prepare_command(command, dargs)
            self.send_command(command, *to_send)
            self.publisher.publish(f'client_outbound_{command.lower()}',
                                   {'contents': dargs.copy()})

        def prepare_command(self, identifier, dargs):
            """
            Prepare a packet so that the client's specific protocol can recognize it.

            Parameters
            ----------
            identifier : str
                ID of the packet to send.
            dargs : dict of str to Any
                Original packet arguments, which will be modified to satisfy the client's protocol.
                Map is of argument name to argument value.

            Returns
            -------
            final_dargs : dict of str to Any
                Modified packet arguments. Map is of argument name to argument value.
            to_send : list of str
                Packet argument values listed in the order the client protocol expects.

            """

            final_dargs = dict()
            to_send = list()
            idn = f'{identifier.upper()}_OUTBOUND'
            try:
                outbound_args = getattr(self.packet_handler, idn)
            except AttributeError:
                err = f'No matching protocol found for {idn}.'
                raise KeyError(err)

            for (field, default_value) in outbound_args:
                try:
                    value = dargs[field]
                    if value is None:
                        value = default_value
                except KeyError:
                    value = default_value
                if field.endswith('ao2_list'):
                    to_send.extend(value)
                else:
                    to_send.append(value)
                final_dargs[field] = value

            self.publisher.publish(f'client_inbound_{identifier.lower()}_raw',
                                   {'contents': final_dargs.copy()})
            return final_dargs, to_send

        def detatch_pair(self):

            if self.charid_pair == -1:
                return
            
            pair_jsn_packet = {}
            pair_jsn_packet['packet'] = 'pair'
            pair_jsn_packet['data'] = {}
            pair_jsn_packet['data']['pair_right'] = int(-1)
            pair_jsn_packet['data']['offset_left'] = int(0)
            pair_jsn_packet['data']['offset_right'] = int(0)

            


            try:
                target, _pair, msg_pair = self.server.client_manager.get_target_public(self, str(self.charid_pair), only_in_area=False)
                target.charid_pair = -1
                pair_jsn_packet['data']['pair_left'] = target.id
                
                json_data = json.dumps(pair_jsn_packet)
                target.send_command_dict('JSN', {
                    'json_data': json_data
                })
                target.send_ooc('You are no longer paired.')
            except:
                pass

            self.charid_pair = -1
            pair_jsn_packet['data']['pair_left'] = self.id
                
            json_data = json.dumps(pair_jsn_packet)
            self.send_command_dict('JSN', {
                'json_data': json_data
            })
            self.send_ooc('You are no longer paired.')

        def send_ooc(
            self,
            msg: str,
            username: str = None,
            allow_empty: bool = False,

            is_staff: Union[bool, None] = None,
            is_officer: Union[bool, None] = None,
            is_mod: Union[bool, None] = None,
            in_hub: Union[bool, _Hub, Set[_Hub], None] = True,
            in_area: Union[bool, AreaManager.Area,
                           Set[AreaManager.Area], None] = None,
            not_to: Union[Set[ClientManager.Client], None] = None,
            part_of: Union[Set[ClientManager.Client], None] = None,
            to_blind: Union[bool, None] = None,
            to_deaf: Union[bool, None] = None,
            is_zstaff: Union[bool, AreaManager.Area, None] = None,
            is_zstaff_flex: Union[bool, AreaManager.Area, None] = None,
            pred: Callable[[ClientManager.Client], bool] = None,
            localization: str = None,
            loc_var_one: str = None,
            loc_var_two: str = None,
        ):
            if not allow_empty and not msg:
                return

            if pred is None:
                def pred(x): return True
            if not_to is None:
                not_to = set()
            if username is None:
                username = self.server.config['hostname']

            cond = Constants.build_cond(
                self,
                is_staff=is_staff,
                is_officer=is_officer,
                is_mod=is_mod,
                in_hub=in_hub,
                in_area=in_area,
                not_to=not_to,
                part_of=part_of,
                to_blind=to_blind,
                to_deaf=to_deaf,
                is_zstaff=is_zstaff,
                is_zstaff_flex=is_zstaff_flex,
                pred=pred
            )

            if cond(self):
                self.send_command_dict('CT', {
                    'username': username,
                    'message': msg,
                    'localization': localization,
                    'variable_one': loc_var_one,
                    'variable_two': loc_var_two
                })

        def send_ooc_others(
            self,
            msg: str,
            username: str = None,
            allow_empty: bool = False,

            is_staff: Union[bool, None] = None,
            is_officer: Union[bool, None] = None,
            is_mod: Union[bool, None] = None,
            in_hub: Union[bool, _Hub, Set[_Hub], None] = True,
            in_area: Union[bool, AreaManager.Area,
                           Set[AreaManager.Area], None] = None,
            not_to: Union[Set[ClientManager.Client], None] = None,
            part_of: Union[Set[ClientManager.Client], None] = None,
            to_blind: Union[bool, None] = None,
            to_deaf: Union[bool, None] = None,
            is_zstaff: Union[bool, AreaManager.Area, None] = None,
            is_zstaff_flex: Union[bool, AreaManager.Area, None] = None,
            pred: Callable[[ClientManager.Client], bool] = None
        ):
            if not allow_empty and not msg:
                return

            if pred is None:
                def pred(x): return True
            if not_to is None:
                not_to = set()
            if username is None:
                username = self.server.config['hostname']

            cond = Constants.build_cond(
                self,
                is_staff=is_staff,
                is_officer=is_officer,
                is_mod=is_mod,
                in_hub=in_hub,
                in_area=in_area,
                not_to=not_to.union({self}),
                part_of=part_of,
                to_blind=to_blind,
                to_deaf=to_deaf,
                is_zstaff=is_zstaff,
                is_zstaff_flex=is_zstaff_flex,
                pred=pred
            )

            self.server.make_all_clients_do("send_ooc", msg, pred=cond, allow_empty=allow_empty,
                                            username=username)

        def send_ic(
            self,
            params: Dict[str, Any] = None,
            sender: Union[ClientManager.Client, None] = None,
            bypass_text_replace: bool = False,
            bypass_deafened_starters: bool = False,
            use_last_received_sprites: bool = False,
            gag_replaced: bool = False,

            is_staff: Union[bool, None] = None,
            is_officer: Union[bool, None] = None,
            is_mod: Union[bool, None] = None,
            in_hub: Union[bool, _Hub, Set[_Hub], None] = True,
            in_area: Union[bool, AreaManager.Area,
                           Set[AreaManager.Area], None] = None,
            not_to: Union[Set[ClientManager.Client], None] = None,
            part_of: Union[Set[ClientManager.Client], None] = None,
            to_blind: Union[bool, None] = None,
            to_deaf: Union[bool, None] = None,
            is_zstaff: Union[bool, AreaManager.Area, None] = None,
            is_zstaff_flex: Union[bool, AreaManager.Area, None] = None,
            pred: Callable[[ClientManager.Client], bool] = None,

            msg=None,
            folder=None,
            pos=None,
            char_id=None,
            ding=None,
            color=None,
            showname=None,
            hide_character=0
        ):

            # sender is the client who sent the IC message
            # self is who is receiving the IC message at this particular moment

            # Assert correct call to the function
            if params is None and msg is None:
                raise ValueError('Expected message.')

            if not_to is None:
                not_to = set()

            # Fill in defaults
            # Expected behavior is as follows:
            #  If params is None, then the sent IC message will only include custom details
            #  about the ding and the message, everything else is fixed. However, sender details
            #  are considered when replacing the parameters based on sender/receiver's properties
            #  If params is not None, then the sent IC message will use the parameters given in
            #  params, and use the properties of sender to replace the parameters if needed.

            pargs = {x: y for (x, y) in self.packet_handler.MS_OUTBOUND}
            if params is None:
                pargs['msg'] = msg
                pargs['folder'] = folder
                pargs['pos'] = pos
                pargs['char_id'] = char_id
                pargs['ding'] = ding
                pargs['color'] = color
                pargs['showname'] = showname
                pargs['hide_character'] = hide_character
            else:
                for key in params:
                    pargs[key] = params[key]
                if msg is not None:
                    pargs['msg'] = msg

            # Check if receiver is actually meant to receive the message. Bail out early if not.
            # FIXME: First argument should be sender, not self. Using in_area=True fails otherwise

            cond = Constants.build_cond(
                self,
                is_staff=is_staff,
                is_officer=is_officer,
                is_mod=is_mod,
                in_hub=in_hub,
                in_area=in_area,
                not_to=not_to,
                part_of=part_of,
                to_blind=to_blind,
                to_deaf=to_deaf,
                is_zstaff=is_zstaff,
                is_zstaff_flex=is_zstaff_flex,
                pred=pred
            )
            if not cond(self):
                return
            # If self is ignoring sender, now is the moment to discard
            if sender and sender in self.ignored_players:
                return

            # FIXME: Workaround because lazy. Proper fix is change all send_ic that specify
            # char_id to also specify sender. However, there are potentially ugly issues lurking
            # with first person/forward sprites mode here which I don't have the heart to figure
            # out right now. Once fixed, remove the upcoming lines.
            # Right now, this feature makes it emulate the old client behavior of ignoring based
            # on character match.
            if char_id:
                for ignored_player in self.ignored_players:
                    if char_id == ignored_player.char_id:
                        return

            # Remove None values from pargs, which could have happened while setting default values
            # from the function call
            to_pop = list()
            for key in pargs:
                if pargs[key] is None:
                    to_pop.append(key)
            for key in to_pop:
                pargs.pop(key)

            def pop_if_there(dictionary, argument):
                if argument in dictionary:
                    dictionary.pop(argument)

            # Change "character" parts of IC port
            if self.is_blind:
                pargs['anim'] = '../../misc/blank'
                pargs['hide_character'] = 1
                self.send_background(
                    name=self.server.config['blackout_background'])
            # If self just spoke while in first person mode, change the message they receive
            # accordingly for them so they do not see themselves talking
            # Also do this replacement if the sender is not in forward sprites mode
            elif (use_last_received_sprites or
                    (sender == self and self.first_person) or
                    (sender and not sender.forward_sprites)):
                # last_sender: Client who actually sent the new message
                # last_seen_sender: Client whose sprites were used for the last message
                # last_args: "MS" arguments to the last message
                # Do note last_sender != last_seen_sender if a person receives a message
                # from someone in not forward sprites mode. In that case, last_sender is
                # updated with this new client, but last apparent_sender is not.

                # First check this is first person mode. By doing this check first we
                # guarantee ourselves we do not pick the last message that could possibly
                # be self
                if sender == self and self.first_person:
                    last_seen_sender, last_args, last_seen_args = self.last_received_ic_notme
                else:
                    last_seen_sender, last_args, last_seen_args = self.last_received_ic

                # Make sure showing previous sender makes sense. If it does not make sense now,
                # it will not make sense later.

                # If last sender is no longer connected, do not show previous sender
                if not last_seen_sender or not self.server.is_client(last_seen_sender):
                    pargs['anim'] = '../../misc/blank'
                    self.last_received_ic_notme = (None, None, None)
                    self.last_received_ic = (None, None, None)
                # If last apparent sender and self are not in the same area, do not show
                # previous sender
                elif self.area != last_seen_sender.area:
                    pargs['anim'] = '../../misc/blank'
                    self.last_received_ic_notme = (None, None, None)
                    self.last_received_ic = (None, None, None)
                # If last sender has changed character, do not show previous sender
                elif ((last_seen_sender.char_id != last_seen_args['char_id'] or
                        last_seen_sender.char_folder != last_seen_args['folder'])):
                    # We need to check for iniswaps as well, to account for this possibility:
                    # 1. A and B are in the same room. A as in first person mode
                    # 2. B talks to A and moves to another room
                    # 3. B iniswaps without changing character and talks in their new area
                    # 4. B goes back to A's area and talks there
                    # 5. If A had received no other message in the meantime, clear the last
                    # character seen.
                    pargs['anim'] = '../../misc/blank'
                    self.last_received_ic_notme = (None, None, None)
                    self.last_received_ic = (None, None, None)
                # Do not show previous sender if
                # 1. Previous sender is sneaked and is not GM, and
                # 2. It is not the case self is in a party, the same one as previous sender,
                # and self is sneaked
                elif (not last_seen_sender.is_visible and
                        not last_seen_sender.is_staff() and
                        not (self.party and self.party == last_seen_sender.party
                             and not self.is_visible)):
                    # It will still be the case self will reveal themselves by talking
                    # They will however see last sender if needed
                    pargs['anim'] = '../../misc/blank'
                    self.last_received_ic_notme = (None, None, None)
                    self.last_received_ic = (None, None, None)
                # Otherwise, show message
                else:
                    pargs['folder'] = last_args['folder']
                    pargs['anim'] = last_args['anim']
                    pargs['pos'] = last_args['pos']
                    pargs['anim_type'] = last_args['anim_type']
                    pargs['flip'] = last_args['flip']
                    # Only DRO 1.1.0+ has this
                    if self.packet_handler.HAS_HIDE_CHARACTER_AS_MS_ARGUMENT:
                        pargs['hide_character'] = last_args['hide_character']

                # Regardless of anything, pairing is visually canceled while in first person
                # so set them to default values

                pop_if_there(pargs, 'other_offset')
                pop_if_there(pargs, 'other_emote')
                pop_if_there(pargs, 'other_flip')
                pop_if_there(pargs, 'other_folder')
                pop_if_there(pargs, 'offset_pair')
                pop_if_there(pargs, 'charid_pair')
                # Note this does not affect the client object internal values, it just
                # simulates the client is not part of their pair if they are in first person
                # mode.
            elif sender != self and self.first_person:
                # Address the situation where this client is in first person mode, paired with
                # someone else, and that someone else speaks in IC. This will 'visually' cancel
                # pairing for this client, but not remove it completely. It is just so that
                # the client's own sprites do not appear.
                if pargs.get('charid_pair', -1) == self.char_id:
                    pop_if_there(pargs, 'other_offset')
                    pop_if_there(pargs, 'other_emote')
                    pop_if_there(pargs, 'other_flip')
                    pop_if_there(pargs, 'other_folder')
                    pop_if_there(pargs, 'offset_pair')
                    pop_if_there(pargs, 'charid_pair')

            # Modify folder as needed
            if self.is_blind and self.is_deaf:
                pargs['folder'] = None

            # Change the message to account for receiver's properties
            if not bypass_text_replace:
                # Change "message" parts of IC port
                allowed_starters = ('(', '*', '[')
                allowed_messages = (' ', '  ')

                # Nerf message for deaf
                # TEMPORARY: REMOVE FOR 4.3+CLIENT UPDATE
                # Remove the send_deaf_space variable eventually
                if self.is_deaf and pargs['msg']:
                    if (bypass_deafened_starters or
                        (not pargs['msg'].startswith(allowed_starters) and
                         not pargs['msg'] in allowed_messages) or
                            (sender and sender.is_gagged and gag_replaced)):
                        pargs['msg'] = '[Your ears are ringing]'
                        if (not self.packet_handler.ALLOWS_REPEATED_MESSAGES_FROM_SAME_CHAR
                                and self.send_deaf_space):
                            pargs['msg'] = pargs['msg'] + ' '
                        self.send_deaf_space = not self.send_deaf_space

                # TEMPORARY: REMOVE FOR 4.3+CLIENT UPDATE
                # Remove globalIC prefix to everyone but sender, but only if in DRO 1.0.0+, to work
                # around old client bug
                if sender and sender.multi_ic and sender.multi_ic_pre:
                    if pargs['msg'].startswith(sender.multi_ic_pre):
                        if (self.packet_handler.ALLOWS_CLEARING_MODIFIED_MESSAGE_FROM_SELF
                                or self != sender):
                            pargs['msg'] = pargs['msg'].replace(
                                sender.multi_ic_pre, '', 1)

                # Modify shownames as needed
                if self.is_blind and self.is_deaf and sender:
                    pargs['showname'] = '???'
                elif self.show_shownames and sender:
                    pargs['showname'] = sender.showname

            # Apply any custom functions
            proper_attributes = {attribute for attribute in pargs
                                 if not attribute.startswith('PER_CLIENT')}
            for proper_attribute in proper_attributes:
                if 'PER_CLIENT_'+proper_attribute in pargs:
                    pargs[proper_attribute] = pargs['PER_CLIENT_' +
                                                    proper_attribute](self)

            # Hide perjury if needed. This would typically be done in NSD code, but if the client
            # is not part of an NSD, this check is not done
            if pargs['button'] == 8:
                keep1 = (
                    'PER_CLIENT_button' in pargs and pargs['PER_CLIENT_button'] == 8)
                keep2 = (self == sender or self.is_staff())
                # Maintain perjury bullet if
                # 1. Specifically mandated by NSD (or some other manipulator of the IC message)
                # 2. Receiver is sender or staff
                # Otherwise convert to counter bullet
                if not (keep1 or keep2):
                    pargs['button'] = 7

            pargs['client_id'] = sender.id if sender else -1

            if pargs['anim'] == '../../misc/blank':
                pargs['hide_character'] = 1

            # Done modifying IC message
            # Now send it

            # This step also takes care of filtering out the packet arguments that the client
            # cannot parse, and also make sure they are in the correct order.
            final_pargs, _ = self.prepare_command('ms', pargs)

            # Keep track of packet details in case this was sent by someone else
            # This is used, for example, for first person mode
            if sender != self or self.is_blind:
                # Blind people are effectively in first person mode
                # So also update as needed.

                # Only update apparent sender if sender was in forward sprites mode
                if sender and sender.forward_sprites:
                    self.last_received_ic_notme = (
                        sender,
                        final_pargs,
                        final_pargs,
                    )
                else:
                    self.last_received_ic_notme = (
                        self.last_received_ic_notme[0],
                        final_pargs,
                        self.last_received_ic_notme[2],
                    )
            # Moreover, keep track of last received IC message
            # This is used for forward sprites mode.
            if sender and sender.forward_sprites:
                self.last_received_ic = (
                    sender,
                    final_pargs,
                    final_pargs,
                )
            else:
                self.last_received_ic = (
                    self.last_received_ic[0],
                    final_pargs,
                    self.last_received_ic[2],
                )

            self.send_command_dict('MS', final_pargs)

        def send_ic_others(
            self,
            params: Dict[str, Any] = None,
            sender: Union[ClientManager.Client, None] = None,
            bypass_text_replace: bool = False,
            bypass_deafened_starters: bool = False,
            use_last_received_sprites: bool = False,
            gag_replaced: bool = False,

            is_staff: Union[bool, None] = None,
            is_officer: Union[bool, None] = None,
            is_mod: Union[bool, None] = None,
            in_hub: Union[bool, _Hub, Set[_Hub], None] = True,
            in_area: Union[bool, AreaManager.Area,
                           Set[AreaManager.Area], None] = None,
            not_to: Union[Set[ClientManager.Client], None] = None,
            part_of: Union[Set[ClientManager.Client], None] = None,
            to_blind: Union[bool, None] = None,
            to_deaf: Union[bool, None] = None,
            is_zstaff: Union[bool, AreaManager.Area, None] = None,
            is_zstaff_flex: Union[bool, AreaManager.Area, None] = None,
            pred: Callable[[ClientManager.Client], bool] = None,

            msg=None,
            folder=None,
            pos=None,
            char_id=None,
            ding=None,
            color=None,
            showname=None,
            hide_character=0
        ):

            if not_to is None:
                not_to = {self}
            else:
                not_to = not_to.union({self})

            cond = Constants.build_cond(
                self,
                is_staff=is_staff,
                is_officer=is_officer,
                is_mod=is_mod,
                in_hub=in_hub,
                in_area=in_area,
                not_to=not_to.union({self}),
                part_of=part_of,
                to_blind=to_blind,
                to_deaf=to_deaf,
                is_zstaff=is_zstaff,
                is_zstaff_flex=is_zstaff_flex,
                pred=pred
            )
            self.server.make_all_clients_do(
                "send_ic",
                pred=cond,
                params=params,
                sender=sender,
                bypass_text_replace=bypass_text_replace,
                bypass_deafened_starters=bypass_deafened_starters,
                use_last_received_sprites=use_last_received_sprites,
                gag_replaced=gag_replaced,
                msg=msg,
                folder=folder,
                pos=pos,
                char_id=char_id,
                ding=ding,
                color=color,
                showname=showname,
                hide_character=hide_character
            )

        def send_ic_attention(self, ding: bool = True):
            int_ding = 1 if ding else 0
            self.send_ic(msg=self.area.noteworthy_text,
                         ding=int_ding, hide_character=1)

        def send_ic_blankpost(self):
            if self.packet_handler.ALLOWS_INVISIBLE_BLANKPOSTS:
                self.send_ic(msg='', hide_character=1,
                             bypass_text_replace=True)

        def send_player_anim(self, animation_name: str = None):
            if animation_name is None:
                return
            self.send_command_dict('ANI', {
                'aniName': animation_name,
                'custom_value': ''
            })

        def send_character_list(self, characters: List[str] = None):
            if characters is None:
                characters = self.hub.character_manager.get_characters()
            self.send_command_dict('SC', {
                'chars_ao2_list': characters,
            })

        def send_investigation(self):
            self.send_command_dict('INVES', {
                'enc_text': self.area.investigation
            })

        def send_weather(self):
            self.send_command_dict('WEA', {
                'name': self.area.weather
            })

        def send_background(self, name: str = None, pos: str = None,
                            tod_backgrounds: Dict[str, str] = None):
            """
            Send a background packet to a client.

            Parameters
            ----------
            name : str, optional
                Background name. The default is None, and converted to the background of the
                client's area.
            pos : str, optional
                Position of the background to send. The default is None, and converted to the
                position of the client.

            Returns
            -------
            None.

            """

            if name is None:
                name = self.area.background
            if pos is None:
                pos = self.pos
            if tod_backgrounds is None:
                tod_backgrounds = dict()

            tod_backgrounds_ao2_list = list()
            for (tod_name, tod_background) in tod_backgrounds.items():
                argument = f'{tod_name}|{tod_background}'
                tod_backgrounds_ao2_list.append(argument)

            self.send_command_dict('BN', {
                'name': name,
                'pos': pos,
                'tod_backgrounds_ao2_list': tod_backgrounds_ao2_list,
            })
            self.send_weather()
            self.send_investigation()


        def send_evidence_list(self):
            self.send_command_dict('LE', {
                'evidence_ao2_list': self.area.get_evidence_list(self)
            })

        def send_health(self, side=None, health=None):
            self.send_command_dict('HP', {
                'side': side,
                'health': health
            })


        def send_music(self, name=None, char_id=None, fade_option=None, showname=None, force_same_restart=None,
                       loop=None, channel=None, effects=None):
            self.send_command_dict('MC', {
                'name': name,
                'char_id': char_id,
                'showname': showname,
                'force_same_restart': force_same_restart,
                'fade_option': fade_option,
                'loop': loop,
                'channel': channel,
                'effects': effects,
            })

        def send_splash(self, name=None):
            self.send_command_dict('RT', {
                'name': name,
            })

        def send_clock(self, client_id=None, hour=None):
            self.send_command_dict('CL', {
                'client_id': client_id,
                'hour': hour,
            })

        def send_gamemode(self, name=None):
            self.ever_outbounded_gamemode = True
            self.send_command_dict('GM', {
                'name': name,
            })

        def send_time_of_day(self, name=None):
            self.ever_outbounded_time_of_day = True
            self.send_command_dict('TOD', {
                'name': name,
            })

        def send_timer_resume(self, timer_id=None):
            self.send_command_dict('TR', {
                'timer_id': timer_id,
            })

        def send_timer_pause(self, timer_id=None):
            self.send_command_dict('TP', {
                'timer_id': timer_id,
            })

        def send_timer_set_time(self, timer_id=None, new_time=None):
            self.send_command_dict('TST', {
                'timer_id': timer_id,
                'new_time': new_time,
            })

        def send_timer_set_step_length(self, timer_id=None, new_step_length=None):
            self.send_command_dict('TSS', {
                'timer_id': timer_id,
                'new_step_length': new_step_length,
            })

        def send_timer_set_firing_interval(self, timer_id=None, new_firing_interval=None):
            self.send_command_dict('TSF', {
                'timer_id': timer_id,
                'new_firing_interval': new_firing_interval,
            })

        def send_showname(self, showname=None):
            self.send_command_dict('SN', {
                'showname': showname,
            })

        def send_chat_tick_rate(self, chat_tick_rate: int = None):
            self.send_command_dict('chat_tick_rate', {
                'chat_tick_rate': chat_tick_rate,
            })

        def send_area_ambient(self, name: str = ''):
            self.send_command_dict('area_ambient', {
                'name': name,
            })

        def send_joined_area(self):
            self.send_command_dict('joined_area', {
            })

        def disconnect(self):
            self.disconnected = True
            self.transport.close()

        def send_motd(self):
            self.send_ooc('=== MOTD ===\r\n{}\r\n============='.format(
                self.server.config['motd']))

        def publish_inbound_command(self, command, dargs):
            self.publisher.publish(f'client_inbound_{command.lower()}',
                                   {'contents': dargs.copy()})

        def is_valid_name(self, name: str) -> bool:
            name_ws = name.replace(' ', '')
            if not name_ws or name_ws.isdigit():
                return False
            # for client in self.hub.get_players():
            #     print(client.name == name)
            #     if client.name == name:
            #         return False
            return True

        @property
        def displayname(self) -> str:
            if self.showname:
                return self.showname
            if self.char_showname:
                return self.char_showname
            return self.get_char_name()

        @property
        def showname_else_char_showname(self) -> str:
            if self.showname:
                return self.showname
            return self.char_showname

        def has_participant_character(self) -> bool:
            return self.hub.character_manager.is_char_id_participant(self.char_id)

        def change_character(self, char_id: int, force: bool = False,
                             target_area: AreaManager.Area = None,
                             old_char: str = None,
                             announce_zwatch: bool = True):
            # Do not run this code if player is still doing server handshake
            if self.char_id is None:
                return

            # Added target_area parameter because when switching areas, the change character code
            # is run before the character's area actually changes, so it would look for the wrong
            # area if I just did self.area
            if target_area is None:
                target_area = self.area
            if old_char is None:
                old_char = self.get_char_name()
            old_char_id = self.char_id

            if not target_area.hub.character_manager.is_valid_character_id(char_id):
                raise ClientError('Invalid character ID.')

            new_char = self.hub.character_manager.get_character_name(char_id)
            if not target_area.is_char_available(char_id, allow_restricted=self.is_staff()):
                if force:
                    for client in self.area.clients:
                        if client.char_id == char_id:
                            client.char_select()
                            if client == self:
                                continue

                            client.send_ooc(
                                'You were forced off your character.')
                            self.send_ooc(
                                f'You forced client {client.id} off their character.')
                            self.send_ooc_others(f'{self.name} [{self.id}] forced client '
                                                 f'{client.id} off their character.',
                                                 is_officer=True, in_hub=None, not_to={client})
                else:
                    raise ClientError(f'Character {new_char} not available.')

            # Code after this comment assumes the character change will be successful
            self.ever_chose_character = True

            has_char_before = self.has_participant_character()
            has_char_after = self.hub.character_manager.is_char_id_participant(
                char_id)

            if has_char_after and not has_char_before:
                # No longer spectator?
                # Now bound by AFK rules
                self.server.task_manager.new_task(self, 'as_afk_kick', {
                    'afk_delay': self.area.afk_delay,
                    'afk_sendto': self.area.afk_sendto,
                })
                # And to lurk callouts, if any, provided not staff member
                self.check_lurk()

                # If they were following someone as a non-GM spectator, stop following
                if not self.is_staff() and self.following:
                    self.send_ooc(f'You stopped following [{self.following.id}] '
                                  f'{self.following.displayname} as you are no longer spectating '
                                  f'and you are not logged in.')
                    self.unfollow_user()

            elif has_char_before and not has_char_after:
                # Now a spectator?
                # No longer bound to AFK rules
                try:
                    self.server.task_manager.delete_task(self, 'as_afk_kick')
                except TaskError.TaskNotFoundError:
                    pass
                # And to lurk callouts
                self.check_lurk()

            self.char_id = char_id
            # Assumes players are not iniswapped initially, waiting for chrini packet
            self.char_folder = new_char
            self.char_showname = ''
            self.pos = 'wit'

            if announce_zwatch:
                self.send_ooc_others('(X) Client {} has changed from character `{}` to `{}` in '
                                     'your zone ({}).'
                                     .format(self.id, old_char, self.char_folder, self.area.id),
                                     is_zstaff=target_area, in_hub=target_area.hub)

            self.send_command_dict('PV', {
                'client_id': self.id,
                'char_id_tag': 'CID',
                'char_id': self.char_id,
            })
            self.send_player_list_to_area()
            self.publisher.publish('client_change_character', {
                'old_char_id': old_char_id,
                'old_char_name': old_char,
                'new_char_id': char_id,
                'new_char_name': new_char,
            })
            logger.log_server('[{}]Changed character from {} to {}.'
                              .format(self.area.id, old_char, self.get_char_name()), self)
            self.add_to_charlog(
                f'Changed character to {self.get_char_name()}.')

        def change_music_cd(self) -> int:
            if self.is_staff():
                return 0

            now = time.time()
            # If we have not played too many tracks recently, return immediately (after recording)
            if len(self.mflood_log) < self.mflood_times:
                self.mflood_log.append(now)
                return 0

            # Otherwise, check if we have changed music too many times.
            earliest = self.mflood_log[0]
            if (now - earliest) < self.mflood_interval:
                # We have flooded the period. Set a mute
                if not self.mute_time:
                    self.mute_time = now
                    return self.mflood_mutelength

            # Check if serving a mute.
            if self.mute_time:
                mute_wait_time = self.mflood_mutelength - \
                    (now - self.mute_time)
                if mute_wait_time > 0:
                    return mute_wait_time

            # Otherwise, we haven't changed music too many times nor serving a mute.
            # 1. If we were previously muted, clear mflood_log
            # 2. Otherwise, only pop first entry
            # In either case, add now time afterwards
            if self.mute_time:
                self.mute_time = 0
                self.mflood_log.clear()
            else:
                self.mflood_log.pop(0)
            self.mflood_log.append(now)
            return 0

        def reload_character(self):
            self.change_character(self.char_id, force=True)

        def get_area_and_music_list_view(self):
            area_list = self.hub.area_manager.get_client_view(
                self, from_area=self.area)
            music_list = self.music_manager.get_legacy_music_list()

            return area_list+music_list
        
        def broadcast_player_list_reason(self, reason : int):
            """
            Send the player list prompt packet to the client.
            """
            area_desc = "Nothing particularly interesting."
            if(self.area.description != "No description."): 
                area_desc = self.area.description
            self.send_command_dict('LIST_REASON', {
                'player_list_reason': reason,
                'player_list_area_info': area_desc
            })
        
        def broadcast_player_list_reason_auto(self):
            """
            Send the player list prompt packet to the client.
            """
            reason = 0
            area_desc = "Nothing particularly interesting."
            if(self.area.description != "No description."): 
                area_desc = self.area.description
            if(not self.area.lobby_area and len(self.area.clients) > 1):
                reason = 2
            if(not self.area.lights):
                area_desc = "The lights are off, so you cannot see anything."
                reason = 1
            if(self.is_blind):
                area_desc = "You can't see anything as you are currently blinded."
                reason = 3

            self.send_command_dict('LIST_REASON', {
                'player_list_reason': reason,
                'player_list_area_info': area_desc
            })

        def send_evidence_to_player(self):
            return_data = {}
            return_data['packet'] = 'evidence'
            
            evidence_to_send = list()
            for evidence_item in self.hub.evidence:
                evidence_data = {}
                evidence_data["name"] = evidence_item.name
                evidence_data["image"] = evidence_item.image
                evidence_data["description"]  = evidence_item.description
                evidence_to_send.append(evidence_data)
                
            return_data['data'] = evidence_to_send

            json_data = json.dumps(return_data)
            self.send_command_dict('JSN', {
                'json_data': json_data
            })

        def send_player_list_to_area(self):
            self.area.broadcast_player_list()                   

        def send_music_list_view(self):
            if self.viewing_hubs:
                area_list = self.hub.manager.get_client_view(self)
            else:
                area_list = self.hub.area_manager.get_client_view(
                    self, from_area=self.area)

            if (self.music_manager.is_default_file_loaded()
                    and self.music_manager.if_default_show_hub_music):
                dro_music_list = self.hub.music_manager.get_music_list()
                ao2_music_list = self.hub.music_manager.get_legacy_music_list()
            else:
                dro_music_list = self.music_manager.get_music_list()
                ao2_music_list = self.music_manager.get_legacy_music_list()

            if self.packet_handler.HAS_DISTINCT_AREA_AND_MUSIC_LIST_OUTGOING_PACKETS:
                # DRO 1.1.0+, KFO and AO2.8.4+ deals with music lists differently than older clients
                # They want the area lists and music lists separate, so they will have it like that
                self.send_command_dict('FA', {
                    'areas_ao2_list': area_list,
                })
                self.send_command_dict('FM', {
                    'music_ao2_list': dro_music_list,
                    'legacy_music_ao2_list': ao2_music_list,
                })
            else:
                self.send_command_dict('FM', {
                    'music_ao2_list': area_list+dro_music_list,
                    'legacy_music_ao2_list': area_list+ao2_music_list,
                })

        def check_change_area(self, area: AreaManager.Area,
                              override_passages: bool = False,
                              override_effects: bool = False,
                              more_unavail_chars: Set[int] = None) -> Tuple[int, List[str]]:
            results = self.area_changer.check_change_area(
                area, override_passages=override_passages, override_effects=override_effects,
                more_unavail_chars=more_unavail_chars)
            return results

        def notify_change_area(self, area: AreaManager.Area, old_char: str,
                               ignore_bleeding: bool = False, ignore_autopass: bool = False,
                               just_me: bool = False) -> Tuple[bool, bool]:
            return self.area_changer.notify_change_area(
                area, old_char, ignore_bleeding=ignore_bleeding, ignore_autopass=ignore_autopass,
                just_me=just_me)

        def check_lurk(self):
            if self.area.lurk_length > 0 and not self.is_staff() and self.has_participant_character():
                self.server.task_manager.new_task(self, 'as_lurk', {
                    'length': self.area.lurk_length,
                })
            else:  # Otherwise, end any existing lurk, if there is one
                try:
                    self.server.task_manager.delete_task(self, 'as_lurk')
                except TaskError.TaskNotFoundError:
                    pass

        def change_hub(self, hub: _Hub,
                       override_effects: bool = False,
                       ignore_bleeding: bool = False, ignore_followers: bool = False,
                       ignore_autopass: bool = False,
                       ignore_checks: bool = False, ignore_notifications: bool = False,
                       more_unavail_chars: Set[int] = None,
                       change_to: int = None, from_party: bool = False):
            if hub == self.hub:
                raise ClientError('User is already in target hub.')

            self.change_area(
                hub.area_manager.default_area(),
                override_passages=True,  # Overriden
                override_effects=override_effects, ignore_bleeding=ignore_bleeding,
                ignore_autopass=ignore_autopass,
                ignore_followers=ignore_followers, ignore_checks=ignore_checks,
                ignore_notifications=ignore_notifications, change_to=change_to,
                more_unavail_chars=more_unavail_chars, from_party=from_party)

        def change_area(self, area: AreaManager.Area,
                        override_passages: bool = False, override_effects: bool = False,
                        ignore_bleeding: bool = False, ignore_followers: bool = False,
                        ignore_autopass: bool = False,
                        ignore_checks: bool = False, ignore_notifications: bool = False,
                        more_unavail_chars: Set[int] = None,
                        change_to: int = None, from_party: bool = False):
            self.area_changer.change_area(
                area, override_passages=override_passages,
                override_effects=override_effects, ignore_bleeding=ignore_bleeding,
                ignore_autopass=ignore_autopass,
                ignore_followers=ignore_followers, ignore_checks=ignore_checks,
                ignore_notifications=ignore_notifications, change_to=change_to,
                more_unavail_chars=more_unavail_chars, from_party=from_party)

        def post_area_changed(self, old_area: Union[None, AreaManager.Area], area: AreaManager.Area,
                              found_something: bool = False,
                              ding_something: bool = False,
                              old_dname: str = '',
                              override_passages: bool = False, override_effects: bool = False,
                              ignore_bleeding: bool = False, ignore_followers: bool = False,
                              ignore_autopass: bool = False,
                              ignore_checks: bool = False, ignore_notifications: bool = False,
                              more_unavail_chars: Set[int] = None, change_to: int = None,
                              from_party: bool = False):
            self.area_changer.post_area_changed(
                old_area, area,
                found_something=found_something,
                ding_something=ding_something,
                old_dname=old_dname,
                override_passages=override_passages,
                override_effects=override_effects,
                ignore_bleeding=ignore_bleeding,
                ignore_followers=ignore_followers,
                ignore_autopass=ignore_autopass,
                ignore_checks=ignore_checks,
                ignore_notifications=ignore_notifications,
                more_unavail_chars=more_unavail_chars,
                change_to=change_to,
                from_party=from_party)

        def change_blindness(self, blind: bool):
            changed = (self.is_blind != blind)
            self.is_blind = blind

            if self.is_blind:
                self.send_ic_blankpost()  # Clear screen
            elif not self.area.lights:
                self.send_background(
                    name=self.server.config['blackout_background'])
            else:
                self.send_background(name=self.area.background,
                                     tod_backgrounds=self.area.get_background_tod())

            found_something, ding_something = self.area_changer.notify_me_rp(
                self.area, changed_visibility=changed, changed_hearing=False)
            if found_something and not blind:
                self.send_ic_attention(ding=ding_something)

        def change_deafened(self, deaf: bool):
            changed = (self.is_deaf != deaf)
            self.is_deaf = deaf

            found_something, ding_something = self.area_changer.notify_me_rp(
                self.area, changed_visibility=False, changed_hearing=changed)
            if found_something and not deaf:
                self.send_ic_attention(ding=ding_something)

        def change_gagged(self, gagged: bool):
            self.is_gagged = gagged

        def check_change_showname(self, showname: str, target_area: AreaManager.Area = None):
            if not showname:
                # Empty shownames are always fine
                return
            if target_area is None:
                target_area = self.area

            if Constants.contains_illegal_characters(showname):
                raise ClientError(
                    f'Showname `{showname}` contains an illegal character.')

            # Check length
            if len(showname) > self.server.config['showname_max_length']:
                raise ClientError("Showname `{}` exceeds the server's character limit of {}."
                                  .format(showname, self.server.config['showname_max_length']))

            # Check if showname is already used within area, and not GM
            if not self.is_staff():
                for c in target_area.clients:
                    if c == self:
                        continue
                    if c.showname == showname or c.char_showname == showname:
                        raise ValueError("Showname `{}` is already in use in this area."
                                         .format(showname))
                        # This ValueError must be recaught, otherwise the client will crash.

        def change_character_ini_details(self, char_folder: str, char_showname: str):
            self.char_folder = char_folder

            # Check if new character showname is valid before updating.
            try:
                if char_showname and self.server.showname_freeze and not self.is_staff():
                    raise ClientError('Shownames are frozen.')
                self.check_change_showname(
                    char_showname, target_area=self.area)
            except (ClientError, ValueError) as exc:
                self.send_ooc(f'Unable to update character showname: {exc}')
            else:
                self.char_showname = char_showname

            self.add_to_charlog(
                f'Changed character ini to {self.char_folder}/{self.char_showname}.')

        def change_showname(self, showname: str, target_area: AreaManager.Area = None,
                            forced: bool = True):
            # forced=True means that someone else other than the user themselves requested the
            # showname change. Should only be false when using /showname.
            if target_area is None:
                target_area = self.area

            self.check_change_showname(showname, target_area=target_area)

            if self.showname != showname:
                status = {True: 'Was', False: 'Self'}
                ctime = Constants.get_time()
                if showname != '':
                    self.showname_history.append("{} | {} set to {}"
                                                 .format(ctime, status[forced], showname))
                else:
                    self.showname_history.append("{} | {} cleared"
                                                 .format(ctime, status[forced]))
                self.send_showname(showname=showname)
            self.showname = showname

        def command_change_showname(self, showname: str, warn_same_name: bool):
            try:
                old_showname = self.showname
                if old_showname == showname:
                    if not warn_same_name:
                        return
                    if old_showname == '':
                        raise ClientError(
                            'You already do not have a showname.')
                    raise ClientError('You already have that showname.')

                if self.server.showname_freeze and not self.is_staff():
                    raise ClientError('Shownames are frozen.')

                try:
                    self.change_showname(showname, forced=False)
                except ValueError:
                    raise ClientError('Given showname `{}` is already in use in this area.'
                                      .format(showname))

                if showname:
                    s_message = 'You have set your showname to `{}`.'.format(
                        showname)
                    if old_showname:
                        w_message = ('(X) Client {} changed their showname from `{}` to `{}` in '
                                     'your zone ({}).'
                                     .format(self.id, old_showname, self.showname, self.area.id))
                    else:
                        w_message = ('(X) Client {} set their showname to `{}` in your zone ({}).'
                                     .format(self.id, self.showname, self.area.id))
                    l_message = '{} set their showname to `{}`.'.format(
                        self.ipid, showname)
                else:
                    s_message = 'You have removed your showname.'
                    w_message = ('(X) Client {} removed their showname `{}` in your zone ({}).'
                                 .format(self.id, old_showname, self.area.id))
                    l_message = '{} removed their showname.'.format(self.ipid)

                self.send_ooc(s_message)
                self.send_ooc_others(w_message, is_zstaff=True)
                logger.log_server(l_message, self)
            except ClientError as exc:
                # Make the client have their old showname
                self.send_showname(showname=self.showname)
                raise exc

        def change_visibility(self, new_status: bool):
            if new_status:  # Changed to visible (e.g. through /reveal)
                self.send_ooc("You are no longer sneaking.")
                self.is_visible = True
                self.send_player_list_to_area()

                # Player should also no longer be under the effect of the server's sneaked handicap.
                # Thus, we check if there existed a previous movement handicap that had a shorter
                # delay than the server's sneaked handicap and restore it (as by default the server
                # will take the largest handicap when dealing with the automatic sneak handicap)
                try:
                    task = self.server.task_manager.get_task(
                        self, 'as_handicap')
                except TaskError.TaskNotFoundError:
                    pass
                else:
                    name = task.parameters['handicap_name']
                    if name == "Sneaking":
                        if self.server.config['sneak_handicap'] > 0 and self.old_handicap:
                            # Only way for a handicap backup to exist and to be in this situation is
                            # for the player to had a custom handicap whose length was shorter than
                            # the server's sneak handicap, then was set to be sneaking, then was
                            # revealed. From this, we can recover the old handicap backup
                            old_length = self.old_handicap.parameters['length']
                            old_name = self.old_handicap.parameters['handicap_name']
                            old_announce_if_over = self.old_handicap.parameters['announce_if_over']

                            msg = ('(X) {} was [{}] automatically imposed their old movement '
                                   'handicap "{}" of length {} seconds after being revealed in '
                                   'area {} ({}).'
                                   .format(self.displayname, self.id, old_name, old_length,
                                           self.area.name, self.area.id))
                            self.send_ooc_others(msg, is_zstaff_flex=True)
                            self.send_ooc('You were automatically imposed your former movement '
                                          'handicap "{}" of length {} seconds when changing areas.'
                                          .format(old_name, old_length))
                            self.server.task_manager.new_task(self, 'as_handicap', {
                                'length': old_length,
                                'handicap_name': old_name,
                                'announce_if_over': old_announce_if_over,
                            })
                        else:
                            self.server.task_manager.delete_task(
                                self, 'as_handicap')

                logger.log_server(
                    '{} is no longer sneaking.'.format(self.ipid), self)
            else:  # Changed to invisible (e.g. through /sneak)
                self.send_ooc("You are now sneaking.")
                self.is_visible = False
                self.send_player_list_to_area()
                self.detatch_pair()
                shandicap = self.server.config['sneak_handicap']
                # Check to see if should impose the server's sneak handicap on the player
                # This should only happen if two conditions are satisfied:
                # 1. There is a positive sneak handicap and,
                # 2. The player has no movement handicap or one shorter than the sneak handicap
                if shandicap > 0:
                    try:
                        task = self.server.task_manager.get_task(
                            self, 'as_handicap')

                        length = task.parameters['length']
                        if length < shandicap:
                            msg = ('(X) {} [{}] was automatically imposed the longer movement '
                                   'handicap "Sneaking" of length {} seconds in area {} ({}).'
                                   .format(self.displayname, self.id, shandicap, self.area.name,
                                           self.area.id))
                            self.send_ooc_others(msg, is_zstaff_flex=True)
                            raise ValueError  # Lazy way to get there, but it works
                    except (TaskError.TaskNotFoundError, ValueError):
                        self.send_ooc('You were automatically imposed a movement handicap '
                                      '"Sneaking" of length {} seconds when changing areas.'
                                      .format(shandicap))
                        self.server.task_manager.new_task(self, 'as_handicap', {
                            'length': shandicap,
                            'handicap_name': 'Sneaking',
                            'announce_if_over': True,
                        })

                logger.log_server(
                    '{} is now sneaking.'.format(self.ipid), self)

        def set_timed_effects(self, effects: Set[Constants.Effects], length: float):
            """
            Parameters
            ----------
            effects: set of Constants.Effect
            length: float
            """

            resulting_effects = dict()

            for effect in effects:
                name = effect.name
                async_name = effect.async_name

                try:
                    task = self.server.task_manager.get_task(self, async_name)
                except TaskError.TaskNotFoundError:
                    self.server.task_manager.new_task(self, async_name, {
                        'length': length,
                        'effect': effect,
                        'new_value': True,
                    })
                    resulting_effects[name] = (length, False)
                else:
                    old_start = task.creation_time
                    old_length = task.parameters['length']
                    # Effect existed before, check if need to replace it with a shorter effect
                    old_remaining, _ = Constants.time_remaining(
                        old_start, old_length)
                    if length < old_remaining:
                        # Replace with shorter timed effect
                        self.server.task_manager.new_task(self, async_name, {
                            'length': length,
                            'effect': effect,
                            'new_value': True,
                        })
                        resulting_effects[name] = (length, True)
                    else:
                        # Do not replace, current effect's time is shorter
                        resulting_effects[name] = (old_remaining, False)

            return resulting_effects

        def change_handicap(self, setting: bool, length: int = 1, name: str = '',
                            announce_if_over: bool = True):
            if setting:
                self.send_ooc('You were imposed a movement handicap "{}" of length {} seconds when '
                              'changing areas.'.format(name, length))

                task = self.server.task_manager.new_task(self, 'as_handicap', {
                    'length': length,
                    'handicap_name': name,
                    'announce_if_over': announce_if_over,
                })
                self.old_handicap = task
                return name
            else:
                try:
                    task = self.server.task_manager.get_task(
                        self, 'as_handicap')
                except TaskError.TaskNotFoundError:
                    raise ClientError
                else:
                    old_name = task.parameters['handicap_name']
                    self.send_ooc('Your movement handicap "{}" when changing areas was removed.'
                                  .format(old_name))
                    self.old_handicap = None
                    self.server.task_manager.delete_task(self, 'as_handicap')

                if self.area.in_zone and self.area.in_zone.is_property('Handicap'):
                    length, name, announce_if_over = self.area.in_zone.get_property(
                        'Handicap')
                    self.send_ooc_others(
                        f'(X) Warning: {self.displayname} [{self.id}] lost '
                        f'their zone movement handicap by virtue of having their '
                        f'handicap removed. Add it again with /zone_handicap_add {self.id}',
                        is_zstaff_flex=True
                    )
                if not self.is_visible and self.server.config['sneak_handicap'] > 0:
                    self.send_ooc_others(
                        f'(X) Warning: {self.displayname} [{self.id}] lost their sneaking handicap '
                        f'by virtue of having their handicap removed. Add it again with /handicap '
                        f'{self.id} {self.server.config["sneak_handicap"]} Sneaking',
                        is_zstaff_flex=True
                    )
                return old_name

        def refresh_remembered_status(self,
                                      area: AreaManager.Area = None) -> List[ClientManager.Client]:
            """
            Update the last remembered statuses of the clients in a given area and return those
            whose remembered status of the client indeed changed.

            Parameters
            ----------
            area : AreaManager.Area
                Area to target. Defaults to None (and converted to self.area)

            Returns
            -------
            clients_to_notify : list of ClientManager.Client
                Clients whose last remembered status of self indeed changed as a result of the call.

            """
            if area is None:
                area = self.area
            # Figure out who to notify if a status has changed from the last one they have seen
            # 0. Self does not get self pings
            # 1. Staff always get pinged the first time/
            # 2. Non-staff get pinged the first time they see someone with different status if:
            # ** That someone is not sneaking
            # ** The lights are on
            # ** Non-staff is not deaf nor deaf
            clients_to_notify = list()

            for other_client in area.clients:
                if other_client == self:
                    continue
                if other_client.is_staff():
                    if self.id not in other_client.remembered_statuses:
                        other_client.remembered_statuses[self.id] = ''

                    if other_client.remembered_statuses[self.id] != self.status:
                        other_client.remembered_statuses[self.id] = self.status
                        clients_to_notify.append(other_client)
                    continue
                if not self.is_visible:
                    continue
                if not area.lights:
                    continue
                if other_client.is_blind or other_client.is_deaf:
                    continue

                if self.id not in other_client.remembered_statuses:
                    other_client.remembered_statuses[self.id] = ''

                if other_client.remembered_statuses[self.id] != self.status:
                    other_client.remembered_statuses[self.id] = self.status
                    clients_to_notify.append(other_client)

            return clients_to_notify

        def follow_user(self, target: ClientManager.Client):
            if target == self:
                raise ClientError('You cannot follow yourself.')
            if target == self.following:
                raise ClientError('You are already following that player.')

            self.send_ooc(f'Began following {target.displayname} [{target.id}] at '
                          f'{Constants.get_time()}.')

            # Notify the player you were following before that you are no longer following them
            # and with notify I mean internally.
            if self.following:
                self.following.followedby.remove(self)
            self.following = target
            target.followedby.add(self)

            if self.area != target.area:
                self.follow_area(target.area, just_moved=False)

            # Warn zone watchers of the area of the target
            self.send_ooc_others(f'(X) {self.displayname} [{self.id}] started following '
                                 f'{target.displayname} [{target.id}] in your zone '
                                 f'({self.area.id}).',
                                 is_zstaff=target.area, in_hub=target.area.hub)

        def unfollow_user(self):
            if not self.following:
                raise ClientError('You are not following anyone.')

            self.send_ooc(f'Stopped following {self.following.displayname} [{self.following.id}] '
                          f'at {Constants.get_time()}.')
            self.send_ooc_others(f'(X) {self.displayname} [{self.id}] stopped following '
                                 f'{self.following.displayname} [{self.following.id}] in your zone '
                                 f'({self.area.id}).',
                                 is_zstaff=self.following.area, in_hub=self.following.area.hub)
            self.following.followedby.remove(self)
            self.following = None

        def follow_area(self, area: AreaManager.Area, just_moved: bool = True):
            # just_moved if True assumes the case where the followed user just moved
            # It being false is the case where, when the following started, the followed user was
            # in another area, and thus the followee is moved automtically

            name = (area.name if area.hub == self.hub
                    else f'{area.name} in hub {area.hub.get_numerical_id()}')

            if just_moved:
                if self.is_staff():
                    self.send_ooc(
                        f'Followed user moved to area {name} at {Constants.get_time()}.')
                else:
                    self.send_ooc(f'Followed user moved to area {name}.')
            else:
                self.send_ooc(f'Followed user was in area {name}.')

            try:
                self.change_area(area, override_passages=True, override_effects=True,
                                 ignore_bleeding=True, ignore_autopass=True, ignore_followers=True)
            except ClientError as error:
                self.send_ooc(f'Unable to follow to area {name}: `{error}`.')

        def send_area_list(self):
            msg = '=== Areas ==='
            lock = {True: '[LOCKED]', False: ''}
            for i, area in enumerate(self.hub.area_manager.get_areas()):
                locked = area.is_modlocked or area.is_locked

                if self.is_staff():
                    n_clt = len(
                        [c for c in area.clients if c.char_id is not None])
                else:
                    n_clt = len(
                        [c for c in area.clients if c.is_visible and c.char_id is not None])

                msg += '\r\nArea {}: {} (users: {}) {}'.format(i,
                                                               area.name, n_clt, lock[locked])
                if self.area == area:
                    msg += ' [*]'
            self.send_ooc(msg)

        def send_limited_area_list(self):
            msg = '=== Areas ==='
            for i, area in enumerate(self.hub.area_manager.get_areas()):
                msg += '\r\nArea {}: {}'.format(i, area.name)
                if self.area == area:
                    msg += ' [*]'
            self.send_ooc(msg)

        def send_limited_hub_list(self):
            msg = '=== Hubs ==='
            for i, hub in self.hub.manager.get_managee_numerical_ids_to_managees().items():
                name = hub.get_name()
                if not name:
                    name = hub.get_id()
                msg += '\r\nHub {}: {}'.format(i, name)
                if self.hub == hub:
                    msg += ' [*]'
            self.send_ooc(msg)

        def get_visible_clients(self, area: AreaManager.Area,
                                mods=False, as_mod=None,
                                only_my_multiclients=False) -> Set[ClientManager.Client]:
            clients = set()

            for c in area.clients:
                # Conditions to print out a target in /getarea(s). All of the following are true:
                # 1. Target is not in the server selection screen and,
                # 2. If mods is True, the target is a mod, and
                # 3. If only_my_multiclients is True, the target is a multiclient of self, and
                # 4. Any of the two:
                # 4.1. self is a staff member (or acting as mod).
                # 4.2. self is not blind, self's area lights are on, and any of the three:
                # 4.2.1. Target is self.
                # 4.2.2. Target is visible.
                # 4.2.3. Target and self are not visible, and are part of the same party.

                if c.char_id is None:
                    continue
                if mods and not c.is_mod:
                    continue
                if only_my_multiclients and c not in self.get_multiclients():
                    continue

                if self.is_staff() or as_mod:
                    clients.add(c)
                elif not self.is_blind and self.area.lights:
                    if c == self:
                        clients.add(c)
                    elif c.is_visible:
                        clients.add(c)
                    elif not self.is_visible and self.party and self.party == c.party:
                        clients.add(c)
            return clients

        def get_area_info(self, area_id: int, mods, as_mod=None, include_shownames=False,
                          include_ipid=None, only_my_multiclients=False):
            if as_mod is None:
                as_mod = self.is_officer()
            if include_ipid is None and as_mod:
                include_ipid = True

            area = self.hub.area_manager.get_area_by_id(area_id)
            clients = self.get_visible_clients(area, mods=mods, as_mod=as_mod,
                                               only_my_multiclients=only_my_multiclients)
            sorted_clients = sorted(clients, key=lambda x: x.get_char_name())

            info = '== Area {}: {} =='.format(area.id, area.name)
            for c in sorted_clients:
                info += '\r\n[{}] {}'.format(c.id, c.get_char_name())
                if c.status:
                    info += ' (!)'
                if include_shownames and c.showname != '':
                    info += ' ({})'.format(c.showname)
                if len(c.get_multiclients()) > 1 and as_mod:
                    # If client is multiclienting add (MC) for officers
                    info += ' (MC)'
                if not c.is_visible:
                    info += ' (S)'
                if include_ipid:
                    info += ' ({})'.format(c.ipid)
            return len(sorted_clients), info

        def send_area_info(self, current_area: AreaManager.Area, area_id: int,
                           mods, as_mod=None, include_shownames=False,
                           include_ipid=None, only_my_multiclients=False):
            info = self.prepare_area_info(current_area, area_id, mods, as_mod=as_mod,
                                          include_shownames=include_shownames,
                                          include_ipid=include_ipid,
                                          only_my_multiclients=only_my_multiclients)
            if info == '':
                info = '\r\n*No players were found in the area range.'
            if area_id == -1:
                info = '== Area List ==' + info
            elif area_id == -2:
                info = '== Zone Area List ==' + info
            self.send_ooc(info)

        def prepare_area_info(self, current_area: AreaManager.Area, area_id: int,
                              mods, as_mod=None,
                              include_shownames=False, include_ipid=None,
                              only_my_multiclients=False):
            # If area_id is -1, then return all areas.
            # If area_id is -2, then return all areas part of self's watched zone
            # If mods is True, then return only mods.
            # If include_shownames is True, then include non-empty custom shownames.
            # If include_ipid is True, then include IPIDs.
            # If only_my_multiclients is True, then include only clients opened by current player
            # Verify that it should send the area info first
            if not self.is_staff() and not as_mod:
                getareas_restricted = (
                    area_id < 0 and not self.area.rp_getareas_allowed)
                getarea_restricted = (
                    area_id >= 0 and not self.area.rp_getarea_allowed)
                if getareas_restricted or getarea_restricted:
                    raise ClientError('This command has been restricted to authorized users only '
                                      'in this area.')
                if not self.area.lights:
                    raise ClientError(
                        'The lights are off, so you cannot see anything.')

            # All code from here on assumes the area info will be sent successfully
            info = ''
            if area_id < 0:
                # all areas info

                if area_id == -1:
                    areas = self.hub.area_manager.get_areas()
                elif area_id == -2:
                    zone = self.zone_watched
                    if zone is None:
                        raise ClientError(
                            f'Client {self.id} is not watching a zone.')
                    areas = sorted(list(zone.get_areas()), key=lambda a: a.id)
                else:
                    raise ValueError(f'Invalid area_id {area_id}')

                for area in areas:
                    # Get area details...
                    # If staff (or acting as mod) and there are clients in the area OR
                    # If not staff, there are visible clients in the area, and one of the following
                    # 1. The client is transient to area passages
                    # 2. The area is the client's area
                    # 3. The area is reachable and visibly reachable from the current one
                    norm_check = (len([c for c in area.clients if c.is_visible or c == self]) > 0
                                  and (self.is_transient
                                       or area == self.area
                                       or (area.name in current_area.visible_areas
                                           and area.name in current_area.reachable_areas)))
                    # Check reachable and visibly reachable to prevent gaining information from
                    # areas that are visible from area list but are not reachable (e.g. normally
                    # locked passages).
                    staff_check = ((self.is_staff() or as_mod)
                                   and area.clients)
                    nonstaff_check = (not self.is_staff() and norm_check)
                    if staff_check or nonstaff_check:
                        num, ainfo = self.get_area_info(area.id, mods, as_mod=as_mod,
                                                        include_shownames=include_shownames,
                                                        include_ipid=include_ipid,
                                                        only_my_multiclients=only_my_multiclients)
                        if num:
                            info += '\r\n{}'.format(ainfo)
            else:
                num, info = self.get_area_info(area_id, mods,
                                               include_shownames=include_shownames,
                                               include_ipid=include_ipid)
                if num == 0:
                    info += '\r\n*No players in this area.'

            return info

        def refresh_char_list(self):
            char_list = [0] * len(self.hub.character_manager.get_characters())
            unusable_ids = self.area.get_chars_unusable(
                allow_restricted=self.is_staff())
            # Remove sneaked players from unusable if needed so that they don't appear as taken
            # Their characters will not be able to be reused, but at least that's one less clue
            # about their presence.
            if not self.is_staff():
                unusable_ids -= {c.char_id for c in self.area.clients if not c.is_visible}

            for x in unusable_ids:
                char_list[x] = -1

            if self.has_participant_character():
                char_list[self.char_id] = 0  # Self is always available
            self.send_command_dict('CharsCheck', {
                'chars_status_ao2_list': char_list,
            })

        def refresh_visible_char_list(self):
            char_list = [0] * len(self.hub.character_manager.get_characters())
            unusable_ids = {c.char_id for c in self.get_visible_clients(self.area)
                            if c.has_participant_character()}
            if not self.is_staff():
                unusable_ids |= {self.hub.character_manager.get_character_id_by_name(name)
                                 for name in self.area.restricted_chars}

            for x in unusable_ids:
                char_list[x] = -1

            # Self is always available
            if self.has_participant_character():
                char_list[self.char_id] = 0
            self.send_command_dict('CharsCheck', {
                'chars_status_ao2_list': char_list,
            })

        def send_done(self):
            self.refresh_visible_char_list()
            self.post_area_changed(None, self.area)

            if self.char_id is None:
                self.char_id = -1  # Set to a valid ID if still needed
            self.send_command_dict('DONE', dict())

        def char_select(self):
            # By running the change_character code, all checks and actions for switching to
            # spectator are made
            self.change_character(-1)
            self.send_done()

        def get_party(self, tc=False):
            if not self.party:
                raise PartyError('You are not part of a party.')
            return self.party

        def add_to_dicelog(self, msg: str):
            if len(self.dicelog) >= 20:
                self.dicelog = self.dicelog[1:]

            info = '{} | {} {}'.format(
                Constants.get_time(), self.displayname, msg)
            self.dicelog.append(info)

        def get_dicelog(self):
            info = '== Roll history of client {} =='.format(self.id)

            if not self.dicelog:
                info += '\r\nThe player has not rolled since joining the server.'
            else:
                for log in self.dicelog:
                    info += '\r\n*{}'.format(log)
            return info

        def is_staff(self):
            """
            Returns True if logged in as 'any' staff role.
            """
            return self.is_mod or self.is_cm or self.is_gm

        def is_officer(self):
            """
            Returns True if logged in as Community Manager or Moderator.
            """
            return self.is_mod or self.is_cm

        def login(self, arg: str, auth_command: Callable[[str, Optional[bool]]], role: str,
                  announce_to_officers: bool = True):
            """
            Wrapper function for the login method for all roles (GM, CM, Mod)
            """
            if len(arg) == 0:
                raise ClientError('You must specify the password.')
            auth_command(arg, announce_to_officers=announce_to_officers)

            # The following actions are true for all logged in roles
            if self.area.evidence_mod == 'HiddenCM':
                self.area.broadcast_evidence_list()
            self.send_music_list_view()  # Update music list to show all areas

            self.send_ooc('Logged in as a {}.'.format(role))
            # Filter out messages about GMs because they were called earlier in auth_gm
            if not self.is_gm and announce_to_officers:
                self.send_ooc_others('{} [{}] logged in as a {}.'.format(self.name, self.id, role),
                                     is_officer=True, in_hub=None)
            logger.log_server('Logged in as a {}.'.format(role), self)

            if self.area.in_zone and self.area.in_zone != self.zone_watched:
                zone_id = self.area.in_zone.get_id()
                self.send_ooc('(X) You are in an area part of zone `{}`. To be able to receive its '
                              'notifications, start watching it with /zone_watch {}'
                              .format(zone_id, zone_id))

            # Send command hints for leading trials and other minigames
            try:
                trial = self.hub.trial_manager.get_managee_of_user(self)
            except TrialError.UserNotPlayerError:
                pass
            else:
                if self not in trial.get_leaders():
                    self.send_ooc(f'(X) You are in an area part of trial `{trial.get_id()}`. To be '
                                  f'able to perform trial administrative actions, start leading it '
                                  f'with /trial_lead')

                try:
                    nsd = trial.get_nsd_of_user(self)
                except TrialError.UserNotInMinigameError:
                    pass
                else:
                    if self not in nsd.get_leaders():
                        self.send_ooc(f'(X) You are in an area part of NSD `{nsd.get_id()}`. '
                                      f'To be able to perform NSD administrative actions, start '
                                      f'leading it with /nsd_lead')

            # No longer bound to AFK rules
            # Nor lurk callouts
            for task_name in ['as_afk_kick', 'as_lurk']:
                try:
                    self.server.task_manager.delete_task(self, task_name)
                except TaskError.TaskNotFoundError:
                    pass

            # No longer need an IC lock bypass
            if self.can_bypass_iclock:
                self.send_ooc('(X) You have lost your IC lock bypass as you logged in as a '
                              'staff member.')
                self.can_bypass_iclock = False

            try:
                self.hub.add_leader(self)
            except HubError.UserAlreadyLeaderError:
                # E.g. logging in as cm after logging in as gm
                pass

        def auth_mod(self, password: str, announce_to_officers: bool = True):
            if self.is_mod:
                raise ClientError('Already logged in.')
            if Constants.secure_eq(password, self.server.config['modpass']):
                self.is_mod = True
                self.is_cm = False
                self.is_gm = False
            else:
                if announce_to_officers:
                    self.send_ooc_others('{} [{}] failed to login as a moderator.'
                                         .format(self.name, self.id), is_officer=True, in_hub=None)
                raise ClientError('Invalid password.')

        def auth_cm(self, password: str, announce_to_officers: bool = True):
            if self.is_cm:
                raise ClientError('Already logged in.')
            if Constants.secure_eq(password, self.server.config['cmpass']):
                self.is_cm = True
                self.is_mod = False
                self.is_gm = False
            else:
                if announce_to_officers:
                    self.send_ooc_others('{} [{}] failed to login as a community manager.'
                                         .format(self.name, self.id), is_officer=True, in_hub=None)
                raise ClientError('Invalid password.')

        def auth_gm(self, password: str, announce_to_officers: bool = True):
            if self.is_gm:
                raise ClientError('Already logged in.')

            hub_pass = self.hub.get_password()
            # Obtain the daily gm pass (changes at midnight server time, gmpass1=Monday..)
            current_day = datetime.datetime.today().weekday()
            daily_gmpass = self.server.config['gmpass{}'.format(
                (current_day % 7) + 1)]

            valid_passwords = [hub_pass, self.server.config['gmpass']]
            if daily_gmpass is not None:
                valid_passwords.append(daily_gmpass)

            for valid_password in valid_passwords:
                if Constants.secure_eq(password, valid_password):
                    break
            else:
                if announce_to_officers:
                    self.send_ooc_others('{} [{}] failed to login as a game master.'
                                         .format(self.name, self.id),
                                         is_officer=True, in_hub=None)
                raise ClientError('Invalid password.')

            if password == hub_pass:
                password_type = 'hub password'
            elif password == daily_gmpass:
                password_type = 'daily password'
            else:
                password_type = 'global password'

            if announce_to_officers:
                self.send_ooc_others('{} [{}] logged in as a game master with the {}.'
                                     .format(self.name, self.id, password_type),
                                     is_officer=True, in_hub=None)
            self.is_gm = True
            self.is_mod = False
            self.is_cm = False

        def logout(self):
            self.is_mod = False
            self.is_gm = False
            self.is_cm = False

            # Clean-up operations
            if self.area.evidence_mod == 'HiddenCM':
                self.area.broadcast_evidence_list()

            # Update the music list to show reachable areas and activate the AFK timer
            self.send_music_list_view()
            self.server.task_manager.new_task(self, 'as_afk_kick', {
                'afk_delay': self.area.afk_delay,
                'afk_sendto': self.area.afk_sendto,
            })

            # If using a character restricted in the area, switch out
            if self.get_char_name() in self.area.restricted_chars:
                try:
                    new_char_id = self.area.get_rand_avail_char_id(
                        allow_restricted=False)
                except AreaError:
                    # Force into spectator mode if all other available characters are taken
                    new_char_id = -1

                old_char = self.get_char_name()
                self.change_character(new_char_id, announce_zwatch=False)
                new_char = self.get_char_name()

                self.send_ooc('Your character has been set to restricted in this area by a staff '
                              'member. Switching you to `{}`.'.format(new_char))
                self.send_ooc_others('(X) Client {} had their character changed from `{}` to `{}` '
                                     'in your zone as their old character was restricted in their '
                                     'area ({}).'
                                     .format(self.id, old_char, new_char, self.area.id),
                                     is_zstaff_flex=True)

            # If watching a zone, stop watching it
            target_zone = self.zone_watched
            if target_zone:
                target_zone.remove_watcher(self)

                self.send_ooc('You are no longer watching zone `{}`.'.format(
                    target_zone.get_id()))
                if target_zone.get_watchers():
                    self.send_ooc_others('(X) {} [{}] is no longer watching your zone.'
                                         .format(self.displayname, self.id),
                                         part_of=target_zone.get_watchers())
                elif target_zone.get_players():
                    self.send_ooc(
                        '(X) Warning: The zone no longer has any watchers.')
                else:
                    self.send_ooc('(X) As you were the last person in an area part of it or who '
                                  'was watching it, your zone has been deleted.')
                    # Not needed, ran in remove_watcher
                    # client.send_ooc_others('Zone `{}` was automatically ended as no one was in '
                    #                        'an area part of it or was watching it anymore.'
                    #                        .format(target_zone.get_id()), is_officer=True)

            # If managing a day cycle clock, end it
            try:
                self.server.task_manager.delete_task(self, 'as_day_cycle')
            except TaskError.TaskNotFoundError:
                pass

            # If having global IC enabled, remove it
            self.multi_ic = None
            self.multi_ic_pre = ''

            # If following someone while not spectator, stop following
            if self.following:
                self.send_ooc(f'You stopped following [{self.following.id}] '
                              f'{self.following.displayname} as you are no longer logged in and '
                              f'you are not a spectator.')
                self.unfollow_user()

            try:
                self.hub.remove_leader(self)
            except HubError.UserNotLeaderError:
                # E.g. logging out as gm
                pass

        def get_hdid(self) -> str:
            return self.hdid

        def get_ip(self) -> int:
            return self.ipid

        def get_ipreal(self) -> str:
            return Constants.get_ip_of_transport(self.transport)

        def get_char_name(self) -> str:
            return self.hub.character_manager.get_character_name(self.char_id)

        def get_showname_history(self) -> str:
            info = '== Showname history of client {} =='.format(self.id)

            if len(self.showname_history) == 0:
                info += '\r\nClient has not changed their showname since joining the server.'
            else:
                for log in self.showname_history:
                    info += '\r\n*{}'.format(log)
            return info

        def change_position(self, pos: str = ''):
            if pos not in ('', 'def', 'pro', 'hld', 'hlp', 'jud', 'wit'):
                raise ClientError('Invalid position. '
                                  'Possible values: def, pro, hld, hlp, jud, wit.')
            self.pos = pos
            self.send_command_dict('SP', {
                'position': self.pos
            })  # Send a "Set Position" packet

        def set_mod_call_delay(self):
            self.mod_call_time = round(time.time() * 1000.0 + 30000)

        def can_call_mod(self) -> bool:
            return (time.time() * 1000.0 - self.mod_call_time) > 0

        def get_multiclients(self) -> List[ClientManager.Client]:
            """
            Return all clients connected to the server that share either the same IPID or same
            HDID as this client, sorted in increasing order by client ID.

            Returns
            -------
            list of ClientManager.Client
                Multiclients.

            """

            ipid = self.server.client_manager.get_targets(
                self, TargetType.IPID, self.ipid, False)
            hdid = self.server.client_manager.get_targets(
                self, TargetType.HDID, self.hdid, False)
            return sorted(set(ipid + hdid))

        def add_to_charlog(self, text: str):
            ctime = Constants.get_time()
            if len(self.char_log) >= 20:
                self.char_log.pop(0)

            self.char_log.append(f'{ctime} | {text}')

        def get_charlog(self) -> str:
            info = '== Character details log of client {} =='.format(self.id)

            if not self.char_log:
                info += ('\r\nClient has not changed their character information since joining the '
                         'server.')
            else:
                for log in self.char_log:
                    info += '\r\n*{}'.format(log)
            return info

        def change_files(self, url):
            if url:
                self.files = [self.char_folder, url]
                self.send_ooc(f'You have set the download link for the files of '
                              f'`{self.char_folder}` to {url}', localization="S_CHAR_SET", loc_var_one=self.char_folder, loc_var_two=url)
                self.send_ooc(f'Let others access them with /files {self.id}', localization="S_CHAR_ACCESS", loc_var_one=str(self.id))
            else:
                if self.files:
                    self.send_ooc(f'You have removed the download link for the files of '
                                  f'`{self.files[0]}`.', localization="S_CHAR_UNSET", loc_var_one=self.files[0])
                    self.files = None
                else:
                    raise ClientError(
                        'You have not provided a download link for your files.')
            self.send_player_list_to_area()

        def get_info(self, as_mod: bool = False, as_cm: bool = False, identifier=None):
            if identifier is None:
                identifier = self.id

            info = '== Client information of {} =='.format(identifier)
            ipid = self.ipid if as_mod or as_cm else "-"
            hdid = self.hdid if as_mod or as_cm else "-"
            info += '\n*CID: {}. IPID: {}. HDID: {}'.format(
                self.id, ipid, hdid)
            info += ('\n*Character name: {}. Showname: {}. OOC username: {}'
                     .format(self.get_char_name(), self.showname, self.name))
            info += ('\n*Actual character folder: {}. Character showname: {}.'
                     .format(self.char_folder, self.char_showname))
            if self.files is None:
                info += ('\n*Character files: Not set.')
            else:
                info += ('\n*Character files: {} | {}'.format(
                    self.files[0], self.files[1]))
            info += '\n*In area: {}-{}'.format(self.area.id, self.area.name)
            info += '\n*Last IC message: {}'.format(self.last_ic_message)
            info += '\n*Last OOC message: {}'.format(self.last_ooc_message)
            info += ('\n*Is GM? {}. Is CM? {}. Is mod? {}.'
                     .format(self.is_gm, self.is_cm, self.is_mod))
            info += ('\n*Is sneaking? {}. Is bleeding? {}. Is handicapped? {}'
                     .format(not self.is_visible, self.is_bleeding, self.is_movement_handicapped))
            info += ('\n*Is blinded? {}. Is deafened? {}. Is gagged? {}'
                     .format(self.is_blind, self.is_deaf, self.is_gagged))
            info += ('\n*Is transient? {}. Has autopass? {}. Clients open: {}'
                     .format(self.is_transient, self.autopass, len(self.get_multiclients())))
            info += '\n*Is muted? {}. Is OOC Muted? {}'.format(
                self.is_muted, self.is_ooc_muted)
            if self.multi_ic is None:
                areas = set()
            else:
                start, end = self.multi_ic[0].id, self.multi_ic[1].id
                areas = {area for area in self.hub.area_manager.get_areas()
                         if start <= area.id <= end}
            info += ('\n*Global IC range: {}. Global IC prefix: {}'
                     .format(Constants.format_area_ranges(areas),
                             'None' if not self.multi_ic_pre else f'`{self.multi_ic_pre}`'))
            info += '\n*Following: {}'.format(
                self.following.id if self.following else "-")
            info += '\n*Followed by: {}'.format(", ".join([str(c.id) for c in self.followedby])
                                                if self.followedby else "-")
            info += '\n*Is Using: {0[0]} {0[1]}'.format(self.version)
            info += ('\n*Online for: {}. Last active: {}'
                     .format(Constants.time_elapsed(self.joined), self.last_active))
            return info

        @property
        def zone_watched(self) -> ZoneManager.Zone:
            """
            Declarator for a public zone_watched attribute.
            """

            return self._zone_watched

        @zone_watched.setter
        def zone_watched(self, new_zone_value):
            """
            Set the zone_watched parameter to the given one.

            Parameters
            ----------
            new_zone_value: ZoneManager.Zone or None
                New zone the client is watching.

            Raises
            ------
            ClientError:
                If the client was not watching a zone and new_zone_value is None or,
                if the client was watching a zone and new_zone_value is not None.
            """

            if new_zone_value is None and self._zone_watched is None:
                raise ClientError(
                    'This client is already not watching a zone.')
            if new_zone_value is not None and self._zone_watched is not None:
                raise ClientError('This client is already watching a zone.')

            self._zone_watched = new_zone_value

        def __lt__(self, other: Any) -> bool:
            """
            If other is an instance of ClientManager.Client, return True if self has lower id
            than other, False otherwise. Otherwise, return the standard Python call of self < other.

            Parameters
            ----------
            other : Any
                Object to compare.

            Raises
            ------
            TypeError
                If self and other cannot be compared.

            Returns
            -------
            bool
                True if self.id < other.id, False otherwise.

            """

            if not isinstance(other, ClientManager.Client):
                return super().__lt__(other)
            return self.id < other.id

        def __repr__(self):
            return ('C::{}:{}:{}:{}:{}:{}:{}:{}'
                    .format(self.id, self.ipid, self.name, self.get_char_name(), self.showname,
                            self.is_staff(), self.area.id, self.hub.get_numerical_id()))

    def __init__(
        self,
        server: TsuserverDR,
        default_client_type: Type[ClientManager.Client] = None,
    ):
        if default_client_type is None:
            default_client_type = self.Client

        self.clients: Set[default_client_type] = set()
        self.server = server
        self.cur_id = [False] * self.server.config['playerlimit']
        self.default_client_type = default_client_type

        # Phantom peek timer stuff
        base_time = 300
        _phantom_peek_timer_min = base_time - base_time/2
        _phantom_peek_timer_max = base_time + base_time/2
        _phantom_peek_fuzz_per_client = base_time/2
        self.phantom_peek_timer = self.server.timer_manager.new_timer(
            auto_restart=True,
            max_value=random.randint(
                int(_phantom_peek_timer_min), int(_phantom_peek_timer_max))
        )

        def _phantom_peek():
            for client in self.clients:
                if client.char_id is None:
                    # Only makes sense for proper players
                    continue
                zone = client.area.in_zone
                if zone and zone.is_property('Paranoia'):
                    zone_paranoia, = zone.get_property('Paranoia')
                else:
                    zone_paranoia = 0
                threshold = (client.paranoia+zone_paranoia)/100
                if random.random() < threshold:
                    delay = random.randint(
                        0, int(_phantom_peek_fuzz_per_client)-1)
                    self.server.task_manager.new_task(client, 'as_phantom_peek', {
                        'length': delay,
                    })
            self.phantom_peek_timer.set_max_value(
                random.randint(int(_phantom_peek_timer_min),
                               int(_phantom_peek_timer_max))
            )

        self.phantom_peek_timer._on_max_end = _phantom_peek
        self.phantom_peek_timer.start()

    def new_client(
        self,
        client_type: Type[Client] = None,
        hub: _Hub = None,
        transport: _ProactorSocketTransport = None,
        protocol: AOProtocol = None,
    ) -> Tuple[Client, bool]:
        if client_type is None:
            client_type = self.default_client_type
        if hub is None:
            hub = self.server.hub_manager.get_default_managee()

        ip = Constants.get_ip_of_transport(transport)
        ipid = self.server.get_ipid(ip)

        cur_id = -1
        for i in range(self.server.config['playerlimit']):
            if not self.cur_id[i]:
                cur_id = i
                break

        c = client_type(self.server, hub, transport,
                        cur_id, ipid, protocol=protocol)
        self.clients.add(c)

        # Check if server is full, and if so, send number of players and disconnect
        if cur_id == -1:
            c.send_command_dict('PN', {
                'player_count': self.server.get_player_count(),
                'player_limit': self.server.config['playerlimit']
            })
            return c, False
        self.cur_id[cur_id] = True
        self.server.task_manager.tasks[c] = dict()
        return c, True

    def remove_client(self, client: ClientManager.Client):
        # Clients who are following the now leaving client should no longer follow them
        if client.followedby:
            followedby_copy = client.followedby.copy()
            for c in followedby_copy:
                c.unfollow_user()

        # Clients who were being followed by the now leaving client should no longer have a pointer
        # indicating they are being followed by them
        if client.following:
            client.following.followedby.remove(client)

        # Avoid having pre-clients do this (before they are granted a cID)
        if client.id >= 0:
            self.cur_id[client.id] = False
            # Cancel client's pending tasks
            for task_name in self.server.task_manager.tasks[client].copy():
                self.server.task_manager.delete_task(client, task_name)

        # If the client was part of a party, remove them from the party
        if client.party:
            client.party.remove_member(client)

        # If the client was watching a zone, remove them from the zone's watcher list, and check if
        # the zone is now empty.
        backup_zone = client.zone_watched

        if backup_zone:
            backup_zone.remove_watcher(client)

            if backup_zone.get_watchers():
                client.send_ooc_others('(X) {} [{}] disconnected while watching your zone ({}).'
                                       .format(client.displayname, client.id, client.area.id),
                                       part_of=backup_zone.get_watchers())
            elif backup_zone.get_players():
                # Do nothing, client would not receive anything anyway as it dc'd
                # client.send_ooc('(X) Warning: The zone no longer has any watchers.')
                pass
            else:
                pass
                # Not needed, ran in remove_watcher
                # client.send_ooc('(X) As you were the last person in an area part of it or who '
                #                 'was watching it, your zone has been deleted.')
                # client.send_ooc_others('Zone `{}` was automatically ended as no one was in '
                #                        'an area part of it or was watching it anymore.'
                #                        .format(backup_zone.get_id()), is_officer=True)

        if client.area.in_zone:
            if client.area.in_zone.is_player(client):
                client.area.in_zone.remove_player(client)

            # If the client was in an area part of a zone, notify all of its watchers except if they
            # have been already notified. This would happen if a client is in an area part of zone A
            # but they are watching some different zone B instead.
            if backup_zone != client.area.in_zone:
                client.send_ooc_others('(X) {} [{}] disconnected in your zone ({}).'
                                       .format(client.displayname, client.id, client.area.id),
                                       is_zstaff=True)

        client.publisher.publish('client_destroyed', {})

        # Moreover, free up the client ID from the set of ignored IDs for all players
        for other in self.clients:
            if client == other:
                continue
            if client.id in other.ignored_players:
                other.ignored_players.remove(client.id)

        # Finally, for every other client, remove the remembered status
        for other in self.clients:
            if client == other:
                continue
            if client.id in other.remembered_statuses:
                other.remembered_statuses.pop(client.id)

        # Moreover, free up the client ID from the set of ignored IDs for all players
        for other in self.clients:
            if client == other:
                continue
            if client.id in other.ignored_players:
                other.ignored_players.remove(client.id)

        client.send_player_list_to_area()
        
        client.detatch_pair()

        self.clients.remove(client)

    def is_client(self, client: ClientManager.Client) -> bool:
        return client in self.clients

    def get_targets(self, client: ClientManager.Client, key: TargetType, value: Any,
                    local: bool = False) -> List[ClientManager.Client]:
        # possible keys: ip, OOC, id, cname, ipid, hdid, showname
        areas = None
        if local:
            areas = [client.area]
        else:
            areas = client.hub.area_manager.get_areas()
        targets = []
        if key == TargetType.ALL:
            for nkey in range(8):
                targets += self.get_targets(client, nkey, value, local)
        for area in areas:
            for target in area.clients:
                if key == TargetType.IP:
                    if target.get_ipreal().lower().startswith(value.lower()):
                        targets.append(target)
                elif key == TargetType.OOC_NAME:
                    if target.name.lower().startswith(value.lower()):
                        targets.append(target)
                elif key == TargetType.CHAR_NAME:
                    if target.get_char_name().lower().startswith(value.lower()):
                        targets.append(target)
                elif key == TargetType.CHAR_FOLDER:
                    if target.char_folder.lower().startswith(value.lower()):
                        targets.append(target)
                elif key == TargetType.ID:
                    if target.id == value:
                        targets.append(target)
                elif key == TargetType.IPID:
                    if target.ipid == value:
                        targets.append(target)
                elif key == TargetType.HDID:
                    if target.hdid == value:
                        targets.append(target)
                elif key == TargetType.SHOWNAME:
                    if target.showname.lower().startswith(value.lower()):
                        targets.append(target)
                elif key == TargetType.CHAR_SHOWNAME:
                    if target.char_showname.lower().startswith(value.lower()):
                        targets.append(target)
        return targets

    def get_muted_clients(self) -> List[ClientManager.Client]:
        clients = []
        for client in self.clients:
            if client.is_muted:
                clients.append(client)
        return clients

    def get_ooc_muted_clients(self) -> List[ClientManager.Client]:
        clients = []
        for client in self.clients:
            if client.is_ooc_muted:
                clients.append(client)
        return clients

    def get_target_public(self, client: ClientManager.Client, identifier: str,
                          only_in_area: bool = False) -> Tuple[ClientManager.Client, str, str]:
        """
        If the first entry of `identifier` is an ID of some client, return that client.
        Otherwise, return the client in the same area as `client` such that one of the
        following is true:
            * Their character name starts with `identifier`
            * Their character they have iniedited to starts with `identifier`
            * Their custom showname starts with `identifier`
            * Their OOC name starts with `identifier`
        Note these criteria are public information for any client regardless of rank.
        If `client` is not a staff member, targets that are sneaking will be discarded if `client`
        is not sneaking or, if they are, they are not part of a party of the same party as the
        target. No output messages will include these discarded targets, even for error messages.

        Parameters
        ----------
        client: ClientManager.Client
            Client whose area will be considered when looking for targets
        identifier: str
            Identifier for target
        only_in_area: bool (optional)
            If search should be limited just to area for parameters guaranteed to be unique as well
            (such as client ID). By default false.

        Returns
        -------
        (ClientManager.Client, str, str)
            Client with an identifier that matches `identifier` as previously described.
            The match that was made, using as much from `identifier` as possible.
            The substring of `identifier` that was not used.

        Raises
        ------
        ClientError:
            If either no clients or more than one client matches the identifier.

        """

        split_identifier = identifier.split(' ')
        multiple_match_mes = ''
        valid_targets = list()

        def _discard_sneaked_if_needed(targets):
            try:
                party_sender = client.get_party()
            except PartyError:
                party_sender = None

            new_targets = set()
            for target in targets:
                if client.is_staff() or target.is_visible:
                    new_targets.add(target)
                # Only consider a sneaked target as valid if the following is true:
                # 1. Client is not visible
                # 2. Client and target are part of the same party
                elif (not client.is_visible and party_sender):
                    try:
                        party_target = target.get_party()
                    except PartyError:
                        party_target = None

                    if party_sender == party_target:
                        new_targets.add(target)
            return new_targets

        for word_number in range(len(split_identifier)):
            # As len(split_identifier) >= 1, this for loop is run at least once, so we can use
            # top-level variables defined here outside the for loop

            # Greedily try and find the smallest possible identifier that gets one unique target
            identity, rest = (' '.join(split_identifier[:word_number+1]),
                              ' '.join(split_identifier[word_number+1:]))
            # First pretend the identity is a client ID, which is unique
            if identity.isdigit():
                targets = set(self.get_targets(
                    client, TargetType.ID, int(identity), only_in_area))
                targets = _discard_sneaked_if_needed(targets)
                if len(targets) == 1:
                    # Found unique match
                    valid_targets = targets
                    valid_match = identity
                    valid_rest = rest
                    break

            # Otherwise, other identifiers may not be unique, so consider all possibilities
            # Pretend the identity is a character name, iniswapped to folder,
            # a showname or OOC name
            possibilities = [
                (TargetType.CHAR_NAME, lambda target: target.get_char_name()),
                (TargetType.CHAR_FOLDER, lambda target: target.char_folder),
                (TargetType.SHOWNAME, lambda target: target.showname),
                (TargetType.CHAR_SHOWNAME, lambda target: target.char_showname),
                (TargetType.OOC_NAME, lambda target: target.name)]
            targets = set()

            # Match against everything
            for possibility in possibilities:
                id_type, id_value = possibility
                new_targets = set(self.get_targets(
                    client, id_type, identity, True))
                new_targets = _discard_sneaked_if_needed(new_targets)
                if new_targets:
                    targets |= new_targets
                    matched = id_value(new_targets.pop())

            if not targets:
                # Covers both the case where no targets were found (at which case no targets will
                # be found later on)
                break
            if len(targets) == 1:
                # Covers the case where exactly one target is found. As the algorithm is meant to
                # produce a greedy result, the for loop will continue in case a larger selection of
                # `identifier` can be matched to a single target.
                valid_targets = targets
                valid_match = matched
                valid_rest = rest
            else:
                # Otherwise, our identity guess was not precise enough, so keep track of that
                # for later and continue with the for loop
                multiple_match_mes = 'Multiple targets match identifier `{}`'.format(
                    identity)
                for target in sorted(list(targets)):
                    char = target.get_char_name()
                    if target.char_folder and target.char_folder != char:  # Show iniswap if needed
                        char = '{}/{}'.format(char, target.char_folder)

                    multiple_match_mes += ('\r\n*[{}] {} ({}) (OOC: {})'
                                           .format(target.id, char, target.showname, target.name))
        if not valid_targets or len(valid_targets) > 1:
            # If was able to match more than one at some point, return that
            if multiple_match_mes:
                raise ClientError(multiple_match_mes)
            # Otherwise, show that no match was ever found
            raise ClientError(
                'No targets with identifier `{}` found.'.format(identifier))

        # For `matched` to be undefined, no targets should have been matched, which would have
        # been caught before.
        return valid_targets.pop(), valid_match, valid_rest
