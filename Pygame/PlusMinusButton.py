import pygame as pg

WHITE = (250, 250, 250)
BLACK = (0, 0, 0)

class PlusMinusButton():
    def __init__(self, x, y, w, h, font, content_w):
        self.content = 0.5
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.font = font
        self.button_w = (w - content_w) / 2
        self.box = pg.Rect(x, y, w, h)
        self.minus_box = pg.Rect(x, y, self.button_w, h)
        self.plus_box = pg.Rect(x + w - self.button_w, y, self.button_w, h)


    def draw(self, surface):
        # Draw main rectangle, plus, minus boxes
        pg.draw.rect(surface, WHITE, self.plus_box, 0)
        pg.draw.rect(surface, WHITE, self.minus_box, 0)
        pg.draw.rect(surface, BLACK, self.box, 3)

        # Draw lines that separate the plus,minus boxes from content window
        pg.draw.line(surface, BLACK, (self.x+self.button_w, self.y), (self.x+self.button_w, self.y+self.h), 3)
        pg.draw.line(surface, BLACK, (self.x+self.w-self.button_w, self.y), (self.x+self.w-self.button_w, self.y+self.h), 3)

        # Draw content
        msg = self.font.render(str(self.content) + 's', 1, BLACK)
        surface.blit(msg, msg.get_rect(center = self.box.center))

        # RENDER PLUS-MINUS IMAGES
        

    def update(self, ev_list):
        mouse = pg.mouse.get_pos()
        for ev in ev_list:
            if ev.type == pg.MOUSEBUTTONDOWN:
                if self.plus_box.collidepoint(mouse) and self.content < 1:
                    self.content = round(self.content + 0.1, 1) # Rounding helps w/ floating-point errors
                if self.minus_box.collidepoint(mouse) and 0 < self.content:
                    self.content = round(self.content - 0.1, 1)
                
        return