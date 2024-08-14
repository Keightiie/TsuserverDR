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

from server.constants import ArgType


class _Singleton():
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(_Singleton, cls).__new__(cls)
        return cls.instance


class DefaultDROProtocol(_Singleton):
    def __eq__(self, other):
        return type(self).__name__ == type(other).__name__

    VERSION_TO_SEND = [1, 3, 0]

    HAS_CLIENTSIDE_MUSIC_LOOPING = True
    HAS_DISTINCT_AREA_AND_MUSIC_LIST_OUTGOING_PACKETS = True
    HAS_ACKMS = False
    HAS_JOINED_AREA = True
    ALLOWS_REPEATED_MESSAGES_FROM_SAME_CHAR = True
    ALLOWS_CLEARING_MODIFIED_MESSAGE_FROM_SELF = True
    ALLOWS_INVISIBLE_BLANKPOSTS = True
    REPLACES_BASE_OPUS_FOR_MP3 = False
    ALLOWS_CHAR_LIST_RELOAD = True
    HAS_HIDE_CHARACTER_AS_MS_ARGUMENT = True

    DECRYPTOR_OUTBOUND = [
        ('key', 34),  # 0
    ]

    HI_INBOUND = [
        ('client_hdid', ArgType.STR),  # 0
    ]

    BD_OUTBOUND = [
    ]

    ID_OUTBOUND = [
        ('client_id', 0),  # 0
        ('server_software', 'TsuserverDR'),  # 1
        ('server_software_version', '0.0.0'),  # 2
    ]

    PN_OUTBOUND = [
        ('player_count', 0),  # 0
        ('player_limit', 0),  # 1
    ]

    LP_OUTBOUND = [
        ('player_data_ao2_list', list()), 
    ]

    JSN_OUTBOUND = [
        ('json_data', ArgType.STR), 
    ]

    LIST_REASON_OUTBOUND = [
        ('player_list_reason', int), 
        ('player_list_area_info', ArgType.STR), 
    ]

    ID_INBOUND = [
        ('client_software', ArgType.STR),  # 0
        ('client_software_version', ArgType.STR),  # 1
    ]

    FL_OUTBOUND = [
        ('fl_ao2_list', list()),  # 0
    ]

    CLIENT_VERSION_OUTBOUND = [
        ('dro_version_ao2_list', list()),  # 0
    ]

    CH_INBOUND = [
        ('char_id', ArgType.INT),  # 0
    ]

    CHECK_OUTBOUND = [
    ]

    ASKCHAA_INBOUND = [
    ]

    SI_OUTBOUND = [
        ('char_count', 0),  # 0
        ('evidence_count', 0),  # 1
        ('music_list_count', 0),  # 2
    ]

    AE_INBOUND = [
        ('evidence_page', ArgType.INT),  # 0
    ]

    RC_INBOUND = [
    ]

    SC_OUTBOUND = [
        ('chars_ao2_list', list()),  # 0
    ]

    RM_INBOUND = [
    ]

    SM_OUTBOUND = [
        ('music_ao2_list', list()),  # 0
    ]

    RD_INBOUND = [
    ]

    CHARSCHECK_OUTBOUND = [
        ('chars_status_ao2_list', list()),  # 0
    ]

    BN_OUTBOUND = [
        ('name', ''),  # 0
        ('tod_backgrounds_ao2_list', list()),  # 1
    ]

    WEA_OUTBOUND = [
        ('name', ''),  # 0
    ]

    LE_OUTBOUND = [
        ('evidence_ao2_list', list()),  # 0
    ]

    MM_OUTBOUND = [
        ('unknown', 1),  # 0
    ]

    PR_INBOUND = [
        ('partner_target', ArgType.INT), 
    ]

    UPR_INBOUND = [
        ('partner_target', ArgType.INT), 
    ]

    POFF_INBOUND = [
        ('pair_offset', ArgType.INT), 
    ]

    PAIR_INBOUND = [
        ('pair_target', ArgType.INT),
        ('response_key', ArgType.STR) 
    ]

    OPPASS_OUTBOUND = [
        ('guard_pass', ''),  # 0
    ]

    DONE_OUTBOUND = [
    ]

    FM_OUTBOUND = [
        ('music_ao2_list', list()),  # 0
    ]

    FA_OUTBOUND = [
        ('areas_ao2_list', list()),  # 0
    ]

    CC_INBOUND = [
        ('client_id', ArgType.INT),
        ('char_id', ArgType.INT),
        ('client_hdid', ArgType.STR),
    ]

    PV_OUTBOUND = [
        ('client_id', 0),  # 0
        ('char_id_tag', 'CID'),  # 1
        ('char_id', -1),  # 2
    ]

    CT_INBOUND = [
        ('username', ArgType.STR),  # 0
        ('message', ArgType.STR),  # 1
    ]

    CT_OUTBOUND = [
        ('username', ''),  # 0
        ('message', ''),  # 1
        ('localization', ''),  # 1
        ('variable_one', ''), # 1
        ('variable_two', ''), # 1
    ]

    ACKMS_OUTBOUND = [
    ]

    MS_INBOUND = [
        ('msg_type', ArgType.STR),  # 0
        ('pre', ArgType.STR_OR_EMPTY),  # 1
        ('folder', ArgType.STR),  # 2
        ('anim', ArgType.STR),  # 3
        ('text', ArgType.STR),  # 4
        ('pos', ArgType.STR),  # 5
        ('sfx', ArgType.STR_OR_EMPTY),  # 6
        ('anim_type', ArgType.INT),  # 7
        ('char_id', ArgType.INT),  # 8
        ('sfx_delay', ArgType.INT),  # 9
        ('button', ArgType.INT),  # 10
        ('evidence', ArgType.INT),  # 11
        ('flip', ArgType.INT),  # 12
        ('ding', ArgType.INT),  # 13
        ('color', ArgType.INT),  # 14
        ('showname', ArgType.STR_OR_EMPTY),  # 15
        ('video', ArgType.STR_OR_EMPTY),  # 16
        ('hide_character', ArgType.INT),  # 17
    ]

    MS_OUTBOUND = [
        ('msg_type', 0),  # 0
        ('pre', '-'),  # 1
        ('folder', '<NOCHAR>'),  # 2
        ('anim', '../../misc/blank'),  # 3
        ('msg', ''),  # 4
        ('pos', 'jud'),  # 5
        ('sfx', 0),  # 6
        ('anim_type', 0),  # 7
        ('char_id', -1),  # 8
        ('sfx_delay', 0),  # 9
        ('button', 0),  # 10
        ('evidence', 0),  # 11
        ('flip', 0),  # 12
        ('ding', -1),  # 13
        ('color', 0),  # 14
        ('showname', ''),  # 15
        ('video', '0'),  # 16
        ('hide_character', 0),  # 17
        ('client_id', -1),  # 18
    ]

    MC_INBOUND = [
        ('name', ArgType.STR),  # 0
        ('char_id', ArgType.INT),  # 1
        ('fade_option', ArgType.INT),  # 2
    ]

    MC_OUTBOUND = [
        ('name', ''),  # 0
        ('char_id', -1),  # 1
        ('showname', ''),  # 2
        ('force_same_restart', 1),  # 3
        ('fade_option', ArgType.INT),  # 4
    ]

    RT_INBOUND = [
        ('name', ArgType.STR),  # 0
    ]

    RT_OUTBOUND = [
        ('name', ''),  # 0
    ]

    HP_INBOUND = [
        ('side', ArgType.INT),  # 0
        ('health', ArgType.INT),  # 1
    ]

    HP_OUTBOUND = [
        ('side', 1),  # 0
        ('health', 0),  # 1
    ]

    PE_INBOUND = [
        ('name', ArgType.STR),  # 0
        ('description', ArgType.STR),  # 1
        ('image', ArgType.STR),  # 2
    ]

    DE_INBOUND = [
        ('evi_id', ArgType.INT),  # 0
    ]

    EE_INBOUND = [
        ('evi_id', ArgType.INT),  # 0
        ('name', ArgType.STR),  # 1
        ('description', ArgType.STR),  # 2
        ('image', ArgType.STR),  # 3
    ]

    ZZ_INBOUND = [
    ]

    ZZ_OUTBOUND = [
        ('message', ''),  # 0
    ]

    SP_OUTBOUND = [
        ('position', ''),  # 0
    ]

    CL_OUTBOUND = [
        ('client_id', 0),  # 0
        ('hour', 0),  # 0
    ]

    TR_OUTBOUND = [
        ('timer_id', 0),  # 0
    ]

    TP_OUTBOUND = [
        ('timer_id', 0),  # 0
    ]

    TST_OUTBOUND = [
        ('timer_id', 0),  # 0
        ('new_time', 0),  # 1
    ]

    TSS_OUTBOUND = [
        ('timer_id', 0),  # 0
        ('new_step_length', 0),  # 1
    ]

    TSF_OUTBOUND = [
        ('timer_id', 0),  # 0
        ('new_firing_interval', 0),  # 1
    ]

    GM_OUTBOUND = [
        ('name', ''),  # 0
    ]

    TOD_OUTBOUND = [
        ('name', ''),  # 0
    ]

    SN_INBOUND = [
        ('showname', ArgType.STR_OR_EMPTY),  # 0
    ]

    SN_OUTBOUND = [
        ('showname', ''),  # 0
    ]

    CHRINI_INBOUND = [
        ('actual_folder_name', ArgType.STR),  # 0
        ('actual_character_showname', ArgType.STR),  # 1
    ]

    CHAT_TICK_RATE_OUTBOUND = [
        ('chat_tick_rate', -1),  # 0
    ]

    CHARSCHECK_INBOUND = [
    ]

    FS_INBOUND = [
        ('url', ArgType.STR_OR_EMPTY),  # 0
    ]

    AREA_AMBIENT_OUTBOUND = [
        ('name', ArgType.STR_OR_EMPTY),  # 0
    ]

    JOINED_AREA_OUTBOUND = [
    ]

class ClientDRO1d7d0(DefaultDROProtocol):
    VERSION_TO_SEND = [1, 7, 0]

    MS_INBOUND = [
        ('client_toggles', ArgType.STR),
        ('char_id', ArgType.INT), 
        ('folder', ArgType.STR),
        ('outfit', ArgType.STR_OR_EMPTY),
        ('pre', ArgType.STR_OR_EMPTY), 
        ('anim', ArgType.STR), 
        ('showname', ArgType.STR_OR_EMPTY),
        ('text', ArgType.STR), 
        ('sfx', ArgType.STR_OR_EMPTY),
        ('sfx_delay', ArgType.INT), 
        ('color', ArgType.INT),
        ('button', ArgType.INT),
        ('ding', ArgType.INT), 
        ('keyframe_anim_name', ArgType.STR_OR_EMPTY),
        ('evidence_name', ArgType.STR_OR_EMPTY),
        ('video', ArgType.STR_OR_EMPTY)
    ]

    MS_OUTBOUND = [
        ('client_toggles', '00'),  # 0  # 7
        ('char_id', -1), 
        ('folder', '<NOCHAR>'),
        ('outfit', ''),
        ('pre', '-'),  # 1  # 2
        ('anim', '../../misc/blank'),
        ('showname', ''), 
        ('msg', ''),  # 5
        ('sfx', 0), 
        ('sfx_delay', 0),
        ('color', 0),
        ('button', 0),
        ('ding', -1), 
        ('keyframe_anim_name', ''), 
        ('evidence_name', ''),  
        ('video', '0'),
        ('client_id', -1),  # 18
        ('server_toggles', '00'),  # 0  # 7
        ('pos', 'jud'), # 6
        ('offset_x', 0), # 19
        ('offset_y', 0), # 19
        ('pair_folder', ''), #20
        ('pair_anim', ''), #21
        ('pair_offset_x', 0),
        ('pair_offset_y', 0)
    ]

    SCENE_OUTBOUND = [
        ('area_name', ArgType.STR),  
        ('bg_image', ArgType.STR),  
        ('map', ArgType.STR)
    ]
    
    INVES_OUTBOUND = [
        ('enc_text', ArgType.STR)
    ]
    
    ANI_OUTBOUND = [
        ('aniName', ArgType.STR),  
        ('custom_value', ArgType.STR)
    ]

    EVA_INBOUND = [
        ('name', ArgType.STR),  # 0
        ('desc', ArgType.STR),  # 1
        ('image', ArgType.STR)  # 2
    ]

    EVR_INBOUND = [
        ('id', ArgType.INT)  # 0
    ]

class ClientDRO1d6d0(DefaultDROProtocol):
    VERSION_TO_SEND = [1, 6, 0]

class ClientDRO1d5d0(DefaultDROProtocol):
    VERSION_TO_SEND = [1, 5, 0]

class ClientDRO1d4d0(DefaultDROProtocol):
    VERSION_TO_SEND = [1, 4, 0]


class ClientDRO1d3d0(DefaultDROProtocol):
    VERSION_TO_SEND = [1, 3, 0]


class ClientDRO1d2d3(DefaultDROProtocol):
    VERSION_TO_SEND = [1, 2, 3]
    HAS_CLIENTSIDE_MUSIC_LOOPING = False

    FM_OUTBOUND = [
        ('legacy_music_ao2_list', list()),  # 0
    ]

    SM_OUTBOUND = [
        ('legacy_music_ao2_list', list()),  # 0
    ]

    MC_INBOUND = [
        ('name', ArgType.STR),  # 0
        ('char_id', ArgType.INT),  # 1
    ]

    MC_OUTBOUND = [
        ('name', ''),  # 0
        ('char_id', -1),  # 1
        ('showname', ''),  # 2
        ('force_same_restart', 1),  # 3
    ]


class ClientDRO1d2d2(ClientDRO1d2d3):
    VERSION_TO_SEND = [1, 2, 2]


class ClientDRO1d2d1(ClientDRO1d2d3):
    VERSION_TO_SEND = [1, 2, 1]


class ClientDRO1d2d0(ClientDRO1d2d3):
    VERSION_TO_SEND = [1, 2, 0]
    ALLOWS_CHAR_LIST_RELOAD = False


class ClientDRO1d1d0(ClientDRO1d2d3):
    VERSION_TO_SEND = [1, 1, 0]
    HAS_JOINED_AREA = False
    ALLOWS_CHAR_LIST_RELOAD = False


class ClientDRO1d0d0(ClientDRO1d2d3):
    VERSION_TO_SEND = [1, 0, 0]
    HAS_DISTINCT_AREA_AND_MUSIC_LIST_OUTGOING_PACKETS = False
    HAS_ACKMS = True
    HAS_JOINED_AREA = False
    REPLACES_BASE_OPUS_FOR_MP3 = True
    ALLOWS_CHAR_LIST_RELOAD = False
    HAS_HIDE_CHARACTER_AS_MS_ARGUMENT = False

    MS_INBOUND = [
        ('msg_type', ArgType.STR),  # 0
        ('pre', ArgType.STR_OR_EMPTY),  # 1
        ('folder', ArgType.STR),  # 2
        ('anim', ArgType.STR),  # 3
        ('text', ArgType.STR),  # 4
        ('pos', ArgType.STR),  # 5
        ('sfx', ArgType.STR_OR_EMPTY),  # 6
        ('anim_type', ArgType.INT),  # 7
        ('char_id', ArgType.INT),  # 8
        ('sfx_delay', ArgType.INT),  # 9
        ('button', ArgType.INT),  # 10
        ('evidence', ArgType.INT),  # 11
        ('flip', ArgType.INT),  # 12
        ('ding', ArgType.INT),  # 13
        ('color', ArgType.INT),  # 14
    ]

    MS_OUTBOUND = [
        ('msg_type', 1),  # 0
        ('pre', '-'),  # 1
        ('folder', '<NOCHAR>'),  # 2
        ('anim', '../../misc/blank'),  # 3
        ('msg', ''),  # 4
        ('pos', 'jud'),  # 5
        ('sfx', 0),  # 6
        ('anim_type', 0),  # 7
        ('char_id', -1),  # 8
        ('sfx_delay', 0),  # 9
        ('button', 0),  # 10
        ('evidence', 0),  # 11
        ('flip', 0),  # 12
        ('ding', -1),  # 13
        ('color', 0),  # 14
        ('showname', ' '),  # 15
    ]

    MC_OUTBOUND = [
        ('name', ''),  # 0
        ('char_id', -1),  # 1
        ('showname', ''),  # 2
    ]


class ClientAO2d10(DefaultDROProtocol):
    HAS_JOINED_AREA = False
    ALLOWS_REPEATED_MESSAGES_FROM_SAME_CHAR = False
    ALLOWS_CLEARING_MODIFIED_MESSAGE_FROM_SELF = False
    ALLOWS_INVISIBLE_BLANKPOSTS = False
    REPLACES_BASE_OPUS_FOR_MP3 = True
    ALLOWS_CHAR_LIST_RELOAD = True
    HAS_HIDE_CHARACTER_AS_MS_ARGUMENT = False

    MS_INBOUND = [
        ('msg_type', ArgType.STR),  # 0
        ('pre', ArgType.STR_OR_EMPTY),  # 1
        ('folder', ArgType.STR),  # 2
        ('anim', ArgType.STR),  # 3
        ('text', ArgType.STR),  # 4
        ('pos', ArgType.STR),  # 5
        ('sfx', ArgType.STR),  # 6
        ('anim_type', ArgType.INT),  # 7
        ('char_id', ArgType.INT),  # 8
        ('sfx_delay', ArgType.INT),  # 9
        ('button', ArgType.INT),  # 10
        ('evidence', ArgType.INT),  # 11
        ('flip', ArgType.INT),  # 12
        ('ding', ArgType.INT),  # 13
        ('color', ArgType.INT),  # 14
        ('showname', ArgType.STR_OR_EMPTY),  # 15
        ('charid_pair_pair_order', ArgType.STR),  # 16
        ('offset_pair', ArgType.STR),  # 17
        ('nonint_pre', ArgType.INT),  # 18
        ('looping_sfx', ArgType.INT),  # 19
        ('screenshake', ArgType.INT),  # 20
        ('frame_screenshake', ArgType.STR_OR_EMPTY),  # 21
        ('frame_realization', ArgType.STR_OR_EMPTY),  # 22
        ('frame_sfx', ArgType.STR_OR_EMPTY),  # 23
        ('additive', ArgType.INT),  # 24
        ('effect', ArgType.STR),  # 25
    ]

    MS_OUTBOUND = [
        ('msg_type', 1),  # 0
        ('pre', '-'),  # 1
        ('folder', '<NOCHAR>'),  # 2
        ('anim', '../../misc/blank'),  # 3
        ('msg', ''),  # 4
        ('pos', 'jud'),  # 5
        ('sfx', 0),  # 6
        ('anim_type', 0),  # 7
        ('char_id', 0),  # 8
        ('sfx_delay', 0),  # 9
        ('button', 0),  # 10
        ('evidence', 0),  # 11
        ('flip', 0),  # 12
        ('ding', -1),  # 13
        ('color', 0),  # 14
        ('showname', ''),  # 15
        ('charid_pair_pair_order', -1),  # 16
        ('other_folder', ''),  # 17
        ('other_emote', ''),  # 18
        ('offset_pair', 0),  # 19
        ('other_offset', 0),  # 20
        ('other_flip', 0),  # 21
        ('nonint_pre', 0),  # 22
        ('looping_sfx', 0),  # 23
        ('screenshake', 0),  # 24
        ('frame_screenshake', ''),  # 25
        ('frame_realization', ''),  # 26
        ('frame_sfx', ''),  # 27
        ('additive', 0),  # 28
        ('effect', ''),  # 29
    ]

    MC_INBOUND = [
        ('name', ArgType.STR),  # 0
        ('char_id', ArgType.INT),  # 1
        ('showname', ArgType.STR_OR_EMPTY),  # 2
        ('effects', ArgType.INT),  # 3
    ]

    MC_OUTBOUND = [
        ('name', ''),  # 0
        ('char_id', -1),  # 1
        ('showname', ''),  # 2
        ('loop', 1),  # 3
        ('channel', 0),  # 4
        ('effects', 0),  # 5
    ]

    BN_OUTBOUND = [
        ('name', ''),  # 0
        ('pos', ''),  # 1
    ]

    PW_INBOUND = [
        ('password', ArgType.STR_OR_EMPTY),  # 0
    ]
