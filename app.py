from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import memprocfs
import struct
import time
import pygame
import pygame_gui
import json
import math
import numpy as np
import os
import re
from requests import get
import threading
import random
from pygame.locals import *


with open(f'config.json', 'r') as f:
    settings = json.load(f)

triangle_length = settings['triangle_length']
circle_size = settings['circle_size']
hp_font_size = settings['hp_font_size']
rot_angle = settings['rot_angle']
cross_size = settings['cross_size']
teammate_setting = settings['teammates']
altgirlpic_instead_nomappic = settings['altgirlpic_instead_nomappic']
update_offsets = settings['update_offsets']
maxclients = int(settings['maxclients'])

#######################################

if update_offsets == 1:
    offsets = get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/generated/offsets.json').json()
    clientdll = get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/generated/client.dll.json').json()
else:
    try:
        with open(f'client.dll.json', 'r') as a:
            clientdll = json.load(a)
        with open(f'offsets.json', 'r') as b:
            offsets = json.load(b)
    except:
        print('[-] put offsets.json and client.dll.json in main folder')
        exit()


#######################################

maps_with_split = ['de_nuke','de_vertigo']
dwEntityList = offsets['client_dll']['data']['dwEntityList']['value']
dwLocalPlayerPawn = offsets['client_dll']['data']['dwLocalPlayerPawn']['value']
m_iPawnHealth = clientdll['CCSPlayerController']['data']['m_iPawnHealth']['value']
m_iPawnArmor = clientdll['CCSPlayerController']['data']['m_iPawnArmor']['value']
m_bPawnIsAlive = clientdll['CCSPlayerController']['data']['m_bPawnIsAlive']['value']
m_angEyeAngles = clientdll['C_CSPlayerPawnBase']['data']['m_angEyeAngles']['value']
m_iTeamNum = clientdll['C_BaseEntity']['data']['m_iTeamNum']['value']
m_hPlayerPawn = clientdll['CCSPlayerController']['data']['m_hPlayerPawn']['value']
m_vOldOrigin = clientdll['C_BasePlayerPawn']['data']['m_vOldOrigin']['value']
m_iIDEntIndex = clientdll['C_CSPlayerPawnBase']['data']['m_iIDEntIndex']['value']
m_iHealth = clientdll['C_BaseEntity']['data']['m_iHealth']['value']
mapNameVal = offsets['matchmaking_dll']['data']['dwGameTypes_mapName']['value']
m_bIsDefusing = clientdll['C_CSPlayerPawnBase']['data']['m_bIsDefusing']['value']
m_bPawnHasDefuser = clientdll['CCSPlayerController']['data']['m_bPawnHasDefuser']['value']
m_iCompTeammateColor = clientdll['CCSPlayerController']['data']['m_iCompTeammateColor']['value']
m_flFlashOverlayAlpha = clientdll['C_CSPlayerPawnBase']['data']['m_flFlashOverlayAlpha']['value']
m_iszPlayerName = clientdll['CBasePlayerController']['data']['m_iszPlayerName']['value']
m_pClippingWeapon = clientdll['C_CSPlayerPawnBase']['data']['m_pClippingWeapon']['value']

print('[+] offsets parsed')

#https://github.com/a2x/cs2-dumper/tree/main/generated

#######################################

zoom_scale = 2
map_folders = [f for f in os.listdir('maps') if os.path.isdir(os.path.join('maps', f))]
global_entity_list = []
playerpawn = 0 

app = FastAPI()

app.mount("/maps", StaticFiles(directory="maps"), name="maps")

html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
</head>
<body>
    <div id="data"></div>
    <script>
        var ws = new WebSocket("ws://localhost:8000/ws");
        ws.onmessage = function(event) {
            let sus = event.data;
            console.log(sus)
        };
    </script>
</body>
</html>
"""

zoom_scale = 2
map_folders = [f for f in os.listdir('maps') if os.path.isdir(os.path.join('maps', f))]
global_entity_list = []
playerpawn = 0 


def get_weapon_name(weapon_id):
    weapon_names = {
        59: "T knife",
        42: "CT knife",
        1: "deagle",
        2: "elite",
        3: "fiveseven",
        4: "glock",
        64: "revolver",
        32: "p2000",
        36: "p250",
        #61: "usp-s",
        262205: "usp-s",
        30: "tec9",
        63: "cz75a",
        17: "mac10",
        24: "ump45",
        26: "bizon",
        33: "mp7",
        34: "mp9",
        19: "p90",
        13: "galil",
        10: "famas",
        60: "m4a1_silencer",
        16: "m4a4",
        8: "aug",
        39: "sg556",
        7: "ak47",
        11: "g3sg1",
        38: "scar20",
        9: "awp",
        40: "ssg08",
        25: "xm1014",
        29: "sawedoff",
        27: "mag7",
        35: "nova",
        28: "negev",
        14: "m249",
        31: "zeus",
        43: "flashbang",
        44: "hegrenade",
        45: "smokegrenade",
        46: "molotov",
        47: "decoy",
        48: "incgrenade",
        49: "c4"
    }

    return weapon_names.get(weapon_id, "Unknown weapon")


def get_weapon(ptr):
    try:
        b1 = struct.unpack("<Q", cs2.memory.read(ptr + m_pClippingWeapon, 8, memprocfs.FLAG_NOCACHE))[0]
        b2 = struct.unpack("<I", cs2.memory.read(b1 + 0x1BA + 0x50 + 0x1098, 4, memprocfs.FLAG_NOCACHE))[0]
        weapon_id = get_weapon_name(b2)
    except:
        return None
    return weapon_id


def world_to_minimap(x, y, pos_x, pos_y, scale, map_image, screen, zoom_scale, rotation_angle):
    try:
        image_x = int((x - pos_x) * screen.get_width() / (map_image.get_width() * scale * zoom_scale))
        image_y = int((y - pos_y) * screen.get_height() / (map_image.get_height() * scale * zoom_scale))
        center_x, center_y = screen_height // 2, screen_width // 2
        image_x, image_y = rotate_point((center_x, center_y), (image_x, image_y), rotation_angle)
        return int(image_x * 0.85), int(image_y * 0.95)
    except:
        return 0,0

def rotate_point(center, point, angle):
    angle_rad = math.radians(angle)
    temp_point = point[0] - center[0], center[1] - point[1]
    temp_point = (temp_point[0]*math.cos(angle_rad)-temp_point[1]*math.sin(angle_rad), temp_point[0]*math.sin(angle_rad)+temp_point[1]*math.cos(angle_rad))
    temp_point = temp_point[0] + center[0], center[1] - temp_point[1]
    return temp_point

def toggle_state():
    global teammate_setting
    teammate_setting = (teammate_setting + 1) % 3

def getmapdata(mapname):
    with open(f'maps/{mapname}/meta.json', 'r') as f:
        data = json.load(f)
    scale = data['scale']
    x = data['offset']['x']
    y = data['offset']['y']
    return scale,x,y

def getlowermapdata(mapname):
    with open(f'maps/{mapname}/meta.json', 'r') as f:
        data = json.load(f)
    lowerx = data['splits']['offset']['x']
    lowery = data['splits']['offset']['y']
    z = data['splits']['zRange']['z']
    return lowerx,lowery,z

def checkissplit(mapname):
    for name in maps_with_split:
        if name in mapname:
            return True


def read_string_memory(address):
    data = b""
    try:
        while True:
            byte = cs2.memory.read(address, 1)
            if byte == b'\0':
                break
            data += byte
            address += 1
        decoded_data = data.decode('utf-8')
        return decoded_data
    except UnicodeDecodeError:
        return data


def readmapfrommem():
    mapNameAddress = struct.unpack("<Q", cs2.memory.read(mapNameAddressbase + mapNameVal, 8, memprocfs.FLAG_NOCACHE))[0]
    mapname = struct.unpack("<32s", cs2.memory.read(mapNameAddress+0x4, 32, memprocfs.FLAG_NOCACHE))[0].decode('utf-8', 'ignore')
    for folder in map_folders:
        if folder in mapname:
            mapname = folder
            break
    if mapname != 'empty':
        print(f"[+] Found map {mapname}")
    mapname = str(mapname)
    return mapname

def get_only_mapname():
    mapNameAddress = struct.unpack("<Q", cs2.memory.read(mapNameAddressbase + mapNameVal, 8, memprocfs.FLAG_NOCACHE))[0]
    mapname = struct.unpack("<32s", cs2.memory.read(mapNameAddress+0x4, 32, memprocfs.FLAG_NOCACHE))[0].decode('utf-8', 'ignore')
    mapname = str(mapname)
    return mapname

def pawnhandler():
    global global_entity_list
    global playerTeam
    global playerpawn
    while True:
        try:
            entityss = getentitypawns()
            if global_entity_list == entityss:
                pass
            else:
                global_entity_list = entityss
            
            playerpawn = struct.unpack("<Q", cs2.memory.read(client_base + dwLocalPlayerPawn, 8, memprocfs.FLAG_NOCACHE))[0]
            playerTeam = struct.unpack("<I", cs2.memory.read(playerpawn + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
        except:
            pass

        time.sleep(10)

def rotate_image(image, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect().center)
    return rotated_image, new_rect

def getentitypawns():
    entitys = []
    EntityList = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
    EntityList = struct.unpack("<Q", cs2.memory.read(EntityList + 0x10, 8, memprocfs.FLAG_NOCACHE))[0]
    for i in range(0,64):
        try:
            EntityAddress = struct.unpack("<Q", cs2.memory.read(EntityList + (i + 1) * 0x78, 8, memprocfs.FLAG_NOCACHE))[0]
            EntityPawnListEntry = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
            Pawn = struct.unpack("<Q", cs2.memory.read(EntityAddress + m_hPlayerPawn, 8, memprocfs.FLAG_NOCACHE))[0]
            EntityPawnListEntry = struct.unpack("<Q", cs2.memory.read(EntityPawnListEntry + 0x10 + 8 * ((Pawn & 0x7FFF) >> 9), 8, memprocfs.FLAG_NOCACHE))[0]
            Pawn = struct.unpack("<Q", cs2.memory.read(EntityPawnListEntry + 0x78 * (Pawn & 0x1FF), 8, memprocfs.FLAG_NOCACHE))[0]
            entitys.append((Pawn, EntityAddress))
        except:
            pass
    return(entitys)


vmm = memprocfs.Vmm(['-device', 'fpga', '-disable-python', '-disable-symbols', '-disable-symbolserver', '-disable-yara', '-disable-yara-builtin', '-debug-pte-quality-threshold', '64'])
cs2 = vmm.process('cs2.exe')
client = cs2.module('client.dll')
client_base = client.base
print(f"[+] Finded client base")

entList = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
print(f"[+] Entered entitylist")


mapNameAddress_dll = cs2.module('matchmaking.dll')
mapNameAddressbase = mapNameAddress_dll.base

EntityList = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
EntityList = struct.unpack("<Q", cs2.memory.read(EntityList + 0x10, 8, memprocfs.FLAG_NOCACHE))[0]

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        mapname = readmapfrommem()
        if 'empty' in mapname:
            mapname = 'empty'
            continue
        if os.path.exists(f'maps/{mapname}'):
            pass
        else:
            print(f'[-] Please, import this map first ({mapname})')
            continue
        if mapname in maps_with_split:
            lowerx,lowery,lowerz = getlowermapdata(mapname)
        scale,x,y = getmapdata(mapname)
        while not 'empty' in get_only_mapname():
            rawjsondata = {"WorldInfo": {"Map": ""},"Players": {}}
            rawjsondata["WorldInfo"]["Map"] = str(mapname)
            try:
                playerpawn = struct.unpack("<Q", cs2.memory.read(client_base + dwLocalPlayerPawn, 8, memprocfs.FLAG_NOCACHE))[0]
                playerTeam = struct.unpack("<I", cs2.memory.read(playerpawn + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
                EntityPawnListEntry = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
                for i in range(maxclients):
                    try:
                        ForbidWrite = True
                        EntityAddress = struct.unpack("<Q", cs2.memory.read(EntityList + (i + 1) * 0x78, 8, memprocfs.FLAG_NOCACHE))[0]
                        Pawn = struct.unpack("<Q", cs2.memory.read(EntityAddress + m_hPlayerPawn, 8, memprocfs.FLAG_NOCACHE))[0]
                        newEntityPawnListEntry = struct.unpack("<Q", cs2.memory.read(EntityPawnListEntry + 0x10 + 8 * ((Pawn & 0x7FFF) >> 9), 8, memprocfs.FLAG_NOCACHE))[0]
                        entity_id = struct.unpack("<Q", cs2.memory.read(newEntityPawnListEntry + 0x78 * (Pawn & 0x1FF), 8, memprocfs.FLAG_NOCACHE))[0]
                        Hp = struct.unpack("<I", cs2.memory.read(entity_id + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
                        if Hp != 0:
                            pX = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x4, 4, memprocfs.FLAG_NOCACHE))[0]
                            pY = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin, 4, memprocfs.FLAG_NOCACHE))[0]
                            pZ = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x8, 4, memprocfs.FLAG_NOCACHE))[0]
                            team = struct.unpack("<I", cs2.memory.read(entity_id + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
                            EyeAngles = struct.unpack("<fff", cs2.memory.read(entity_id +(m_angEyeAngles +0x4) , 12, memprocfs.FLAG_NOCACHE))
                            EyeAngles = math.radians(EyeAngles[0]+rot_angle)
                            isdefusing = struct.unpack("<I", cs2.memory.read(entity_id + m_bIsDefusing, 4, memprocfs.FLAG_NOCACHE))[0]
                            flash_alpha = int(struct.unpack("<f", cs2.memory.read(entity_id + m_flFlashOverlayAlpha, 4, memprocfs.FLAG_NOCACHE))[0])
                            if checkissplit(mapname):
                                if pZ<lowerz:
                                    x, y = lowerx, lowery
                                else:
                                    pass
                            else:
                                pass
                            if teammate_setting == 2:
                                if team == playerTeam:
                                    color = struct.unpack("<I", cs2.memory.read(EntityAddress + m_iCompTeammateColor, 4, memprocfs.FLAG_NOCACHE))[0]
                                elif team != playerTeam:
                                    color = 6
                                    name = read_string_memory(EntityAddress + m_iszPlayerName)
                                    weapon = get_weapon(entity_id)
                            elif teammate_setting == 1:
                                if team == playerTeam:
                                    color = 7
                                elif team != playerTeam:
                                    color = 6
                                    name = read_string_memory(EntityAddress + m_iszPlayerName)
                                    weapon = get_weapon(entity_id)
                                    wepname.append((name, weapon))
                            elif teammate_setting == 0:
                                if entity_id == playerpawn:
                                    color = 7
                                elif team == playerTeam:
                                    ForbidWrite = False
                                elif team != playerTeam:
                                    color = 6
                                    name = read_string_memory(EntityAddress + m_iszPlayerName)
                                    weapon = get_weapon(entity_id)
                            if isdefusing == 1:
                                isdefusing = True
                        if Hp != 0:
                            player_data = {
                                "pX": str(pX),
                                "pY": str(pY),
                                "x": str(pX),
                                "y": str(pY),
                                "EyeAngles": str(EyeAngles),
                                "scale": str(scale),
                                "isDefusing": str(isdefusing),
                                "FlashAlpha": str(flash_alpha),
                                "Color": str(color),
                                "HP": str(Hp),
                                "Weapon": str(weapon)
                            }
                            rawjsondata["Players"][str(i)] = player_data
                    except:
                        continue
                await websocket.send_text(rawjsondata)        
            except Exception as e:
                print(e)


        
        
