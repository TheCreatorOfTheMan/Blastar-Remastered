import struct
import types
from typing import *

import pygame

# * Tuple[int, int] and List[int] will both usually refer to position
# * The reason there are two types used is since Tuple is immutable and
# * Sometimes that proves a problem when updating position so List[int]
# * is used instead


class CollisionBox:
    def __init__(self, top_left: List[int], dimensions: List[int]):
        self.top_left = top_left
        self.dimensions = dimensions
        self.bottom_right = [
            self.top_left[0] + self.dimensions[0],
            self.top_left[1] + self.dimensions[1]
        ]

    def inside(self, pos: Tuple[int, int]) -> bool:
        if (pos[0] <= self.bottom_right[0] and pos[0] >= self.top_left[0]) and (pos[1] >= self.top_left[1] and pos[1] <= self.bottom_right[1]):
            return True
        return False

    def update(self, top_left: Tuple[int, int]):
        self.top_left = top_left
        self.bottom_right = [
            self.top_left[0] + self.dimensions[0],
            self.top_left[1] + self.dimensions[1]
        ]


class Velocity:
    def __init__(self, x: int, y: int, falloff: float, persistent: bool, maxSpeed: float):
        self.x = x
        self.y = y
        self.maxSpeed = maxSpeed
        self._falloff = falloff  # ? Falloff is immutable
        self.finished = False
        # ? Persistency defines whether or not a velocity should finish
        self.persistent = persistent

    def apply(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        if self.persistent == True:
            return self.applyLogic(pos)

        if self.finished == False:
            if int(self.x) == 0 and int(self.y) == 0:
                self.finished = True
            else:
                return self.applyLogic(pos)
        return (pos[0], pos[1])

    def applyLogic(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        result = (pos[0] + self.x, pos[1] + self.y)

        # * Note to self: Don't try to shrink this code since that ain't gonna happen
        # * The reason why there must be similar code in different clauses is because if
        # * the velocity was initialized positive, then MIN value of clamping is different
        # * (in this case it should be 0) than if velocity was initialized negative in which
        # * the MAX value should be 0

        # * Here's a nice ASCII visual

        # * Positive velocity: [ -inf ----0---- inf ]
        # *                    Clamp  :   ^      ^

        # * Negative velocity: [ -inf ----0---- inf ]
        # *             Clamp  :   ^      ^

        if self.x < 0:  # ? Apply the falloff to x
            self.x += self._falloff
            self.x = clamp(self.x, -self.maxSpeed, 0)
        elif self.x > 0:
            self.x -= self._falloff
            self.x = clamp(self.x, 0, self.maxSpeed)

        if self.y < 0:  # ? Apply the falloff to y
            self.y += self._falloff
            self.y = clamp(self.y, -self.maxSpeed, 0)
        elif self.y > 0:
            self.y -= self._falloff
            self.y = clamp(self.y, 0, self.maxSpeed)

        return result

    def __str__(self):
        return f"[{round(self.x, 1)}|{round(self.y, 1)}]"

    def asTuple(self) -> Tuple:
        return (self.x, self.y)

    def fromTuple(self, inp: Tuple[int, int]):
        self.x = inp[0]
        self.y = inp[1]

    def toBytes(self) -> bytes:
        # ? Velocity as Bytes Protocol Description:
        # ? Buffer size: 17 Bytes
        # ? [4 Bytes (float) X] | [4 Bytes (float) Y] | [4 Bytes (float) maxSpeed] | [4 Bytes (float) falloff] | [1 Byte (Bool) persistency]
        return struct.pack("!ffff?", self.x, self.y, self.maxSpeed, self._falloff, self.persistent)


class SpaceObject:
    def __init__(self, pos: List[int], scr: pygame.display, sprite: pygame.Surface, dead: pygame.Surface, velocityQueue: List[Velocity], maxVelStack: int, maxVelSpeed: int, onWallCollided, onCollision, givenID: str, velocityFalloff: float):
        self.id = givenID
        self.isDead = False

        self.onWallCollided = onWallCollided
        self.onCollision = onCollision

        self.pos = pos
        self.velocityFalloff = velocityFalloff
        self.maxVelSpeed = maxVelSpeed
        self.velocity = Velocity(0, 0, velocityFalloff, True, maxVelSpeed)
        self.maxVelocityStack = maxVelStack
        self.velocityQueue = velocityQueue

        self.screen = scr

        self.sprite = sprite
        self.dead = dead

        self.active = self.sprite

        self.dimensions = self.sprite.get_rect().size
        self.collisionBox = CollisionBox(self.pos, self.dimensions)

    def die(self):
        self.active = self.dead
        self.isDead = True

        # * I'll admit, this is a bit of a "hacky" solution but
        # * it achieves what I want cleanly in one line and that's
        # * really all I care about
        self.tick = types.MethodType(self.deathTick, self)

    def addForce(self, vel: Velocity, callback = lambda vel : None):
        if len(self.velocityQueue) != self.maxVelocityStack:
            self.velocityQueue.append(vel)
            callback(vel)

    def deathTick(self, s1, objs):  # ? Empty tick function, only renders dead sprite to screen
        # ? These two other arguments aren't used although I'm assuming s1 refers to 'self' and 'objs' refers to the attribute children of the game instance
        self.screen.blit(self.active, self.pos)

    def tick(self, objs):
        if len(self.velocityQueue) != 0:
            self.velocity.fromTuple(
                self.velocityQueue[0].apply(self.velocity.asTuple()))
            if self.velocityQueue[0].finished == True:
                self.velocityQueue.pop(0)

        self.pos = list(self.velocity.apply(self.pos))

        self.onWallCollided(self)

        self.collisionBox.update(self.pos)

        # * This collision detection method is very inefficient, however I don't have any better methods so it's just gonna stay here
        for obj in objs:
            if obj != self:
                if obj.collisionBox.inside(tuple(self.pos)) or \
                        obj.collisionBox.inside(tuple(self.collisionBox.bottom_right)) or \
                        obj.collisionBox.inside((self.collisionBox.top_left[0], self.collisionBox.bottom_right[1])) or \
                        obj.collisionBox.inside((self.collisionBox.bottom_right[0], self.collisionBox.top_left[1])):

                    self.onCollision(self, obj)

        self.screen.blit(self.active, self.pos)

    def toBytes(self):
        # ? SpaceObject as Bytes Protocol Description:
        # ? Buffer size: 20 Bytes
        # ? [4 Bytes (int) X] | [4 Bytes (int) Y] | [4 Bytes (int) maxVelStack] | [4 Bytes (int) maxVelSpeed] | [4 Bytes (float) velocityFalloff]
        return struct.pack("!IIIIf", self.pos[0], self.pos[1], self.maxVelocityStack, self.maxVelSpeed, self.velocityFalloff)


class Game:
    def __init__(self, screen: pygame.display, children: List[SpaceObject], deathDuration: int):
        self.screen = screen
        self.children = children
        self.deathDuration = deathDuration
        self.deathCleanup = {}
        self.frame = 0

    def summon(self, obj: SpaceObject):  # ? Spawning method for spawning space objects
        self.children.append(obj)
        self.tick()

    def kill(self, *args: SpaceObject):  # ? Kill method for killing space objects
        self.deathCleanup[self.frame + self.deathDuration] = args
        for obj in args:
            obj.die()
        self.tick()

    def tick(self):  # ? Called every frame, you can imagine it is what displays stuff onto the screen and also what makes the game's "time" progress
        for child in self.children:
            child.tick(self.children)

        if self.frame in self.deathCleanup.keys():
            for obj in self.deathCleanup[self.frame]:
                try:
                    self.children.remove(obj)
                except:
                    pass
        self.frame += 1


def clamp(n, least, most):
    return max(least, min(n, most))


def velocityFromBytes(b):
    velocityParams = struct.unpack("!ffff?", b)
    return Velocity(velocityParams[0], velocityParams[1], velocityParams[3], velocityParams[4],  velocityParams[2])


def spaceObjectFromBytes(b, scr, sprite, dead, onWallCollided, onCollision, givenID):
    spaceObjectParams = struct.unpack("!IIIIf", b)
    return SpaceObject(
        [
            spaceObjectParams[0],
            spaceObjectParams[1]
        ],
        scr, sprite, dead, [],
        spaceObjectParams[2],
        spaceObjectParams[3],
        onWallCollided,
        onCollision,
        givenID, spaceObjectParams[4]
    )
