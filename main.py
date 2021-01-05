# ------------------------------------------------------- #
# Blastar Remastered                                      #
#   by: Sid and Krish                                     #
#                                                         #
# "If I had gone to the point of adding velocity maybe    #
#   I should've included a whole physics engine as well"  #
#                       -I, who regrets everything, 2021  #
#                                                         #
# "That's right I waited to 2021 to actually start        #
#   seriously cracking down on this project."             #
#             -I, who didn't really regret that one, 2021 #
#                                                         #
# "Probably should've written tests."                     #
# ------------------------------------------------------- #

# Note: This game is best played natively

import random
import socket
import sys
import threading

import pygame
from pygame.locals import *

from core import *


class GenericController():
    def __init__(self):
        # ? Settings (I know somebody's gonna change something in here and cheat D:<)
        self.scrDimensions = (800, 800)

        self.targetFPS = 144

        self.gameSpeedFactor = 1000

        self.deathFrames = round(self.targetFPS * 0.5, 0)
        self.speed = 0.2
        self.maxSpeed = 5
        self.falloff = 0.1

        # ? Init

        pygame.init()

        self.screen = pygame.display.set_mode(self.scrDimensions)

        self.player = SpaceObject(
            pos=[random.randint(20, self.scrDimensions[0] - 20),
                 random.randint(20, self.scrDimensions[1] - 20)],
            scr=self.screen,
            sprite=pygame.image.load("player.png"),
            dead=pygame.image.load("player_death.png"),
            velocityQueue=[],
            maxVelStack=1,
            maxVelSpeed=self.maxSpeed,
            onWallCollided=self.limitPlayers,
            onCollision=self.onAllCollided,
            givenID="Player",
            velocityFalloff=self.falloff
        )

        self.game = Game(self.screen, [self.player], self.deathFrames)

    def run(self):
        # ? Some text rendering stuff
        WHITE = (255, 255, 255)
        BLACK = (0, 0, 0)

        fontsize = 20
        font = pygame.font.SysFont(None, fontsize)
        w, h = self.screen.get_size()

        self.clock = pygame.time.Clock()

        while True:
            self.clock.tick(self.targetFPS)

            fps = self.clock.get_fps()
            if fps == 0:
                fps = 1

            keystate = pygame.key.get_pressed()

            if keystate[pygame.K_LEFT]:
                self.player.addForce(
                    Velocity(-self.speed * (self.gameSpeedFactor / fps), 0,
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed)
                )
            if keystate[pygame.K_RIGHT]:
                self.player.addForce(
                    Velocity(self.speed * (self.gameSpeedFactor / fps), 0,
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed)
                )
            if keystate[pygame.K_UP]:
                self.player.addForce(
                    Velocity(0, -self.speed * (self.gameSpeedFactor / fps),
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed)
                )
            if keystate[pygame.K_DOWN]:
                self.player.addForce(
                    Velocity(0, self.speed * (self.gameSpeedFactor / fps),
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed)
                )
            if keystate[pygame.K_SPACE]:  # ? Shoot
                # * This is not a great solution especially for lower frame rates however it will do for now
                if self.game.frame % round(self.targetFPS * 0.15, 0) == 0 and self.player.isDead == False:
                    self.game.summon(SpaceObject(
                        pos=self.player.pos,
                        scr=self.screen,
                        sprite=pygame.image.load("player_bullet.png"),
                        dead=pygame.Surface((0, 0)),
                        velocityQueue=[
                            Velocity(0, -2 * (self.gameSpeedFactor / fps), 0, False, 6)],
                        maxVelStack=2,
                        maxVelSpeed=4,
                        onWallCollided=self.limitBullet,
                        onCollision=self.onAllCollided,
                        givenID="Player_Bullet",
                        velocityFalloff=self.falloff
                    ))
            if keystate[pygame.K_ESCAPE]:
                pygame.quit()
                sys.exit()

            for vel, i in zip(self.player.velocityQueue, range(len(self.player.velocityQueue))):
                img = font.render(str(vel), True, BLACK)
                self.screen.blit(
                    img, (5, h-fontsize*len(self.player.velocityQueue) + fontsize*i)
                )

            img = font.render(str(int(fps)), True, BLACK)
            self.screen.blit(img, (5, 0))

            self.game.tick()

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()
            self.screen.fill(WHITE)

    def limitPlayers(self, obj):
        obj.pos[0] = clamp(obj.pos[0], 0, self.scrDimensions[0])
        obj.pos[1] = clamp(obj.pos[1], 0, self.scrDimensions[1])

    def onAllCollided(self, obj, target):
        if obj.id not in target.id and target.id not in obj.id:
            self.game.kill(obj, target)

    def limitBullet(self, obj):
        if (obj.pos[0] <= 0 or obj.pos[0] >= self.scrDimensions[0]) or (obj.pos[1] <= 0 or obj.pos[1] >= self.scrDimensions[1]):
            self.game.kill(obj)


class SingleplayerController(GenericController):
    def __init__(self):
        super().__init__()
        self.game.summon(SpaceObject(
            pos=[random.randint(20, self.scrDimensions[0] - 20),
                 random.randint(20, self.scrDimensions[1] - 20)],
            scr=self.screen,
            sprite=pygame.image.load("enemy.png"),
            dead=pygame.image.load("enemy_death.png"),
            velocityQueue=[],
            maxVelStack=1,
            maxVelSpeed=self.maxSpeed,
            onWallCollided=self.limitPlayers,
            onCollision=self.onAllCollided,
            givenID="Enemy",
            velocityFalloff=self.falloff
        ))


# ? Network Protcol Packet Types:
# ? -----------------------------------
# ? 0: Player Join
# ? 1: Player Velocity
# ? 2: Velocity Sync
# ? 3: SpaceObject Summon
# ? 4: SpaceObject Kill
# ? 5: Player Quit

class NetworkController(GenericController):
    def __init__(self):
        super().__init__()

    def run(self, addr: str, port: int):
        self.player.onVelocityFinish = self.onVelocityFinishCallback

        self.remoteAddr = (addr, port)

        self.opponents = {}

        self.opponentSprite = pygame.image.load("enemy.png")
        self.opponentDead = pygame.image.load("enemy_death.png")

        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # ? Packet Type 0: Player Join
        self.client.sendto(b"\x00" + self.player.toBytes(), self.remoteAddr)

        self.recvThread = threading.Thread(
            target=self.packetHandler, daemon=True)
        self.recvThread.start()

        WHITE = (255, 255, 255)
        BLACK = (0, 0, 0)

        fontsize = 20
        font = pygame.font.SysFont(None, fontsize)
        w, h = self.screen.get_size()

        self.clock = pygame.time.Clock()

        while True:
            self.clock.tick(self.targetFPS)

            fps = self.clock.get_fps()
            if fps == 0:
                fps = 1

            keystate = pygame.key.get_pressed()

            if keystate[pygame.K_LEFT]:
                self.player.addForce(
                    Velocity(-self.speed * (self.gameSpeedFactor / fps), 0,
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed),
                    self.addForceNetworkCallback
                )
            if keystate[pygame.K_RIGHT]:
                self.player.addForce(
                    Velocity(self.speed * (self.gameSpeedFactor / fps), 0,
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed),
                    self.addForceNetworkCallback
                )
            if keystate[pygame.K_UP]:
                self.player.addForce(
                    Velocity(0, -self.speed * (self.gameSpeedFactor / fps),
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed),
                    self.addForceNetworkCallback
                )
            if keystate[pygame.K_DOWN]:
                self.player.addForce(
                    Velocity(0, self.speed * (self.gameSpeedFactor / fps),
                             self.falloff * (self.gameSpeedFactor / fps), False, self.maxSpeed),
                    self.addForceNetworkCallback
                )
            if keystate[pygame.K_SPACE]:  # ? Shoot
                # * This is not a great solution especially for lower frame rates however it will do for now
                if self.game.frame % round(self.targetFPS * 0.15, 0) == 0 and self.player.isDead == False:
                    self.game.summon(SpaceObject(
                        pos=self.player.pos,
                        scr=self.screen,
                        sprite=pygame.image.load("player_bullet.png"),
                        dead=pygame.Surface((0, 0)),
                        velocityQueue=[
                            Velocity(0, -2 * (self.gameSpeedFactor / fps), 0, False, 6)],
                        maxVelStack=2,
                        maxVelSpeed=4,
                        onWallCollided=self.limitBullet,
                        onCollision=self.onAllCollided,
                        givenID="Player_Bullet",
                        velocityFalloff=self.falloff
                    ))
            if keystate[pygame.K_ESCAPE]:
                pygame.quit()
                sys.exit()

            for vel, i in zip(self.player.velocityQueue, range(len(self.player.velocityQueue))):
                img = font.render(str(vel), True, BLACK)
                self.screen.blit(
                    img, (5, h-fontsize*len(self.player.velocityQueue) + fontsize*i)
                )

            img = font.render(str(int(fps)), True, BLACK)
            self.screen.blit(img, (5, 0))

            self.game.tick()

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()
            self.screen.fill(WHITE)

    # ? Packet type 1: Velocity
    def addForceNetworkCallback(self, vel: Velocity):
        self.client.sendto(b"\x01" + vel.toBytes(), self.remoteAddr)

    # ? Packet type 2: Sync
    def onVelocityFinishCallback(self, vel: Velocity, obj: SpaceObject):
        if len(obj.velocityQueue) == 0:
            self.client.sendto(
                b"\x02" + constructSyncBytes(obj.pos, vel), self.remoteAddr
            )

    def packetHandler(self):
        while True:
            b, addr = self.client.recvfrom(256)
            if b[1] == 0:  # ? Handle Player Join
                print(b)
                buff = b[2:]
                if self.opponents.get(b[0]) == None:
                    self.client.sendto(
                        b"\x00" + self.player.toBytes(), self.remoteAddr)
                    self.opponents[b[0]] = spaceObjectFromBytes(
                        buff, self.screen, self.opponentSprite, self.opponentDead, self.limitPlayers, self.onAllCollided, f"Player_{b[0]}")
                    self.game.summon(self.opponents[b[0]])
            elif b[1] == 1:  # ? Handle Velocity
                buff = b[2:]
                self.opponents[b[0]].addForce(velocityFromBytes(buff))
            elif b[1] == 2:  # ? Handle Sync
                buff = b[2:]
                syncParams = interpretSyncBytes(buff)
                print(syncParams)
                distX = self.opponents[b[0]].pos[0] - syncParams[0][0]
                distY = self.opponents[b[0]].pos[1] - syncParams[0][1]
                if distY == 0:
                    for i in range(distX // syncParams[1].x):
                        self.opponents[b[0]].velocityQueue.append(syncParams[1])
                elif distX == 0:
                    for i in range(distY // syncParams[1].y):
                        self.opponents[b[0]].velocityQueue.append(syncParams[1])
                else:
                    print("Encountered a diagonal!")
            else:
                break

    # ? Packet type 4: Player Quit
    def quit(self):
        self.client.sendto(b"\x05")


if __name__ == "__main__":
    menu = open("menu.txt", "r")
    print(menu.read())
    mode = int(input(" > "))
    if mode == 0:
        game = SingleplayerController()
        game.run()
    elif mode == 1:
        print("Specify Multiplayer Server Address")
        addr = input(" > ")
        print("Specify Multiplayer Server Port")
        port = int(input(" > "))

        game = NetworkController()
        game.run(addr, port)
