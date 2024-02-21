from flask import Flask, render_template, jsonify
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

########## ADJUST SIZES HERE ##########

triangle_length = 13
circle_size = 7 # 8 too big
hp_font_size = 18
rot_angle = 0

#######################################

maps_with_split = ['de_nuke','de_vertigo']
dwEntityList = 0x18B3FA8 # offsets.py
dwLocalPlayerPawn = 0x1729348 #offsets.py
m_iPawnHealth = 0x7F0
m_iPawnArmor = 0x7F4
m_bPawnIsAlive = 0x7EC
m_angEyeAngles = 0x1578
m_iTeamNum = 0x3CB
m_hPlayerPawn = 0x7E4
m_vOldOrigin = 0x127C
m_iIDEntIndex = 0x15A4
m_iHealth = 0x334
mapNameVal = 0x1D2300

#https://github.com/a2x/cs2-dumper/tree/main/generated

#######################################

zoom_scale = 2


def world_to_minimap(x, y, pos_x, pos_y, scale, map_image, screen, zoom_scale, rotation_angle):
    image_x = int((x - pos_x) * screen.get_width() / (map_image.get_width() * scale * zoom_scale))
    image_y = int((y - pos_y) * screen.get_height() / (map_image.get_height() * scale * zoom_scale))
    center_x, center_y = screen.get_width() // 2, screen.get_height() // 2
    image_x, image_y = rotate_point((center_x, center_y), (image_x, image_y), rotation_angle)
    return int(image_x), int(image_y)

def rotate_point(center, point, angle):
    angle_rad = math.radians(angle)
    temp_point = point[0] - center[0], center[1] - point[1]
    temp_point = (temp_point[0]*math.cos(angle_rad)-temp_point[1]*math.sin(angle_rad), temp_point[0]*math.sin(angle_rad)+temp_point[1]*math.cos(angle_rad))
    temp_point = temp_point[0] + center[0], center[1] - temp_point[1]
    return temp_point

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

def readmapfrommem():
    mapNameAddress_dll = cs2.module('matchmaking.dll')
    mapNameAddressbase = mapNameAddress_dll.base
    mapNameAddress = struct.unpack("<Q", cs2.memory.read(mapNameAddressbase + mapNameVal, 8, memprocfs.FLAG_NOCACHE))[0]
    mapName = struct.unpack("<32s", cs2.memory.read(mapNameAddress+0x4, 32, memprocfs.FLAG_NOCACHE))[0].decode('utf-8', 'ignore')
    return str(mapName)

def rotate_image(image, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect().center)
    return rotated_image, new_rect

def getentitys():
    vmm = memprocfs.Vmm(['-device', 'fpga', '-disable-python', '-disable-symbols', '-disable-symbolserver', '-disable-yara', '-disable-yara-builtin', '-debug-pte-quality-threshold', '64'])
    cs2 = vmm.process('cs2.exe')
    client = cs2.module('client.dll')

    client_base = client.base
    print(f"[+] Finded client base")

    entList = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
    print(f"[+] Entered entitylist")
    entitys = []
    for entityId in range(1,2048):
        EntityENTRY = struct.unpack("<Q", cs2.memory.read((entList + 0x8 * (entityId >> 9) + 0x10), 8, memprocfs.FLAG_NOCACHE))[0]
        try:
            entity = struct.unpack("<Q", cs2.memory.read(EntityENTRY + 120 * (entityId & 0x1FF), 8, memprocfs.FLAG_NOCACHE))[0]
            entityHp = struct.unpack("<I", cs2.memory.read(entity + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
            if entityHp>0 and entityHp<=100:
                entitys.append(entity)
            else:
                pass
        except:
            pass
    return(entitys)

class player1:
    def __init__(self, entity_id):
        self.entity_id = entity_id
        self.pX = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x4, 4, memprocfs.FLAG_NOCACHE))[0]
        self.pY = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin, 4, memprocfs.FLAG_NOCACHE))[0]
        self.pZ = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x8, 4, memprocfs.FLAG_NOCACHE))[0]
        self.Hp = struct.unpack("<I", cs2.memory.read(entity_id + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
        self.team = struct.unpack("<I", cs2.memory.read(entity_id + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
        self.EyeAngles = struct.unpack("<fff", cs2.memory.read(entity_id +(m_angEyeAngles +0x4) , 12, memprocfs.FLAG_NOCACHE))
        self.EyeAngles = math.radians(self.EyeAngles[0]+rot_angle)

    def to_dict(self):
        return {
            'entity_id': self.entity_id,
            'position': {'x': self.pX, 'y': self.pY, 'z': self.pZ},
            'hp': self.Hp,
            'team': self.team,
            'eye_angles': self.EyeAngles
        }
def get_players_data():
    entities = getentitys()
    players = [player1(entity_id).to_dict() for entity_id in entities]
    return players


app = Flask(__name__)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    return jsonify(players)

@app.route('/players')
def players():
    players_data = get_players_data()
    return jsonify(players_data)

if __name__ == '__main__':
    app.run(debug=True)