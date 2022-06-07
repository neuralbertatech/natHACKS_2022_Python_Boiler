import pygame as pg
import os

cactus = pg.image.load(os.path.join(os.getcwd(), "Pygame", "assets", "cactus.png"))
cactus = pg.transform.scale(cactus, (100, 100))
bullet = pg.image.load(os.path.join(os.getcwd(), "Pygame", "assets", "bullet.png"))
bullet = pg.transform.scale(bullet, (30, 30))
dinosaur = pg.image.load(os.path.join(os.getcwd(), "Pygame", "assets", "dinosaur.gif"))
dinosaur = pg.transform.scale(dinosaur, (100, 100))

class Cactus(pg.sprite.Sprite):

    # Constructor. Pass in the color of the block,
    # and its x and y position
    def __init__(self, width, height):
        # Call the parent class (Sprite) constructor
        pg.sprite.Sprite.__init__(self)

        # Create an image of the block, and fill it with a color.
        # This could also be an image loaded from the disk.
        self.image = cactus

        # Fetch the rectangle object that has the dimensions of the image
        # Update the position of this object by setting the values of rect.x and rect.y
        self.rect = self.image.get_rect()
        self.rect.x = width
        self.rect.y = height

    def update(self):
         self.rect.x -= 10
         return

class Bullet(pg.sprite.Sprite):

    # Constructor. Pass in the color of the block,
    # and its x and y position
    def __init__(self, width, height):
        # Call the parent class (Sprite) constructor
        pg.sprite.Sprite.__init__(self)

        # Create an image of the block, and fill it with a color.
        # This could also be an image loaded from the disk.
        self.image = bullet

        # Fetch the rectangle object that has the dimensions of the image
        # Update the position of this object by setting the values of rect.x and rect.y
        self.rect = self.image.get_rect()
        self.rect.x = width
        self.rect.y = height

    def update(self):
         self.rect.x += 20
         return

class Dinosaur(pg.sprite.Sprite):

    # Constructor. Pass in the color of the block,
    # and its x and y position
    def __init__(self, width, height):
        # Call the parent class (Sprite) constructor
        pg.sprite.Sprite.__init__(self)

        # Create an image of the block, and fill it with a color.
        # This could also be an image loaded from the disk.
        self.image = dinosaur

        # Fetch the rectangle object that has the dimensions of the image
        # Update the position of this object by setting the values of rect.x and rect.y
        self.rect = self.image.get_rect()
        self.rect.x = width
        self.rect.y = height