from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import struct
import math
import time
import threading

class player1:
    def __init__(self, entity_id):
        self.entity_id = entity_id

def getentitys():
    entitys = []
    for entityId in range(1,2048):
        EntityENTRY = struct.unpack("<Q", cs2.memory.read((entList + 0x8 * (entityId >> 9) + 0x10), 8, memprocfs.FLAG_NOCACHE))[0]
        try:
            entity = struct.unpack("<Q", cs2.memory.read(EntityENTRY + 120 * (entityId & 0x1FF), 8, memprocfs.FLAG_NOCACHE))[0]
            entityHp = struct.unpack("<I", cs2.memory.read(entity + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
            if entityHp>0 and entityHp<=100:
                entitys.append(entity)
        except:
            pass
    return entitys

def update_data(player):
    player.pX = struct.unpack("<f", cs2.memory.read(player.entity_id + m_vOldOrigin +0x4, 4, memprocfs.FLAG_NOCACHE))[0]
    player.pY = struct.unpack("<f", cs2.memory.read(player.entity_id + m_vOldOrigin, 4, memprocfs.FLAG_NOCACHE))[0]
    player.pZ = struct.unpack("<f", cs2.memory.read(player.entity_id + m_vOldOrigin +0x8, 4, memprocfs.FLAG_NOCACHE))[0]
    player.Hp = struct.unpack("<I", cs2.memory.read(player.entity_id + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
    player.team = struct.unpack("<I", cs2.memory.read(player.entity_id + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
    player.EyeAngles = struct.unpack("<fff", cs2.memory.read(player.entity_id +(m_angEyeAngles +0x4) , 12, memprocfs.FLAG_NOCACHE))
    player.EyeAngles = math.radians(player.EyeAngles[0]+rot_angle)

def update_loop():
    while True:
        entity_ids = getentitys()
        for entity_id in entity_ids:
            player = player1(entity_id)
            update_data(player)

update_thread = threading.Thread(target=update_loop)
update_thread.start()

@csrf_exempt
def game_view(request):
    if request.method == 'GET':
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CS2 Game</title>
            <style>
                #game {
                    position: relative;
                    width: 1024px;
                    height: 1024px;
                    background-image: url('/maps/de_mirage/radar.png');
                }
                .player {
                    position: absolute;
                    width: 10px;
                    height: 10px;
                }
                .team2 {
                    background-color: red;
                }
                .team3 {
                    background-color: blue;
                }
            </style>
        </head>
        <body>
            <div id="game"></div>
            <script src="/static/js/game.js"></script>
        </body>
        </html>
        """
        return HttpResponse(html)
    elif request.method == 'POST':
        data = {
            'players': [
                {
                    'pX': player.pX,
                    'pY': player.pY,
                    'pZ': player.pZ,
                    'Hp': player.Hp,
                    'team': player.team,
                    'EyeAngles': player.EyeAngles
                }
                for player in players
            ]
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

urlpatterns = [
    path('game/', game_view, name='game'),
]
