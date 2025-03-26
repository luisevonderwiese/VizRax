import pygame
import os
import shutil
import math
import time

from PIL import Image, ImageOps


import numpy as np
import pygame_menu as pm
import matplotlib.pyplot as plt

################### TREE DRAWING ############################################################


class State:
    def __init__(self, x, y, angle, length, width):
        self.x = x
        self.y = y
        self.angle = angle
        self.length = length
        self.width = width

ANGLE_OFFSET = (27 * 2 * np.pi) / 360




def resize_with_padding(path, expected_size):
    img = Image.open(path)
    delta_width = expected_size - img.size[0]
    delta_height = expected_size - img.size[1]
    pad_width = delta_width // 2
    pad_height = delta_height // 2
    padding = (pad_width, pad_height, delta_width - pad_width, delta_height - pad_height)
    img = ImageOps.expand(img, padding, fill = (255, 255, 255))
    img.save(path)




######################## UI FUNCTIONS ##################################


def draw_bar(screen, s):
    cursor = BAR_MARGIN

    pygame.draw.rect(screen, (255, 255, 255), pause_button)
    if s.done:
        screen.blit(icons["resume"], icons["resume"].get_rect(center = pause_button.center))
    elif s.paused:
        screen.blit(icons["play"], icons["play"].get_rect(center = pause_button.center))
    else:
        screen.blit(icons["pause"], icons["pause"].get_rect(center = pause_button.center))
    pygame.draw.rect(screen, (255, 255, 255), autoplay_button)
    if s.autoplay:
        screen.blit(icons["infinity"], icons["infinity"].get_rect(center = autoplay_button.center))
    else:
        screen.blit(icons["no_infinity"], icons["no_infinity"].get_rect(center = autoplay_button.center))


def refresh(screen, s):
    screen.fill((255, 255, 255))
    if s.image is not None:
        screen.blit(s.image, (TREE_MARGIN, TREE_MARGIN))
    draw_bar(screen, s)
    pygame.display.flip()



######################### DATA SETTINGS #######################################



def init_dir():
    if os.path.isdir("temp"):
        shutil.rmtree("temp")
    os.makedirs("temp")






######################### SIZES ##################################################
pygame.init()
infoObject = pygame.display.Info()
screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h), pygame.RESIZABLE)
pygame.display.set_caption("VizRax")
icon = pygame.image.load(os.path.join("icons", "horse.png"))
pygame.display.set_icon(icon)

SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_surface().get_size()

BAR_HEIGHT = int(SCREEN_HEIGHT * 0.2 * 0.8)
BAR_MARGIN = int(SCREEN_HEIGHT * 0.2 * 0.2)
BAR_Y_POS = SCREEN_HEIGHT - BAR_HEIGHT + BAR_MARGIN*0.5

BUTTON_SIZE = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) / 20)

LEFT_WIDTH = min(SCREEN_WIDTH // 2, SCREEN_HEIGHT - (BAR_HEIGHT + BAR_MARGIN))
RIGHT_WIDTH = min(SCREEN_WIDTH // 2, SCREEN_HEIGHT - (BAR_HEIGHT + BAR_MARGIN))
TREE_MARGIN = LEFT_WIDTH * 0.1




#################### COLORS ####################
GREEN_COLOR = (99, 224, 49)  # Green color for the box around thumbnails


################## FONTS ######################################
pygame.font.init()
font = pygame.font.Font(os.path.join("fonts", 'MiriamLibre-Regular.ttf'), 30)



################# ICONS #################################
icons = {}
for icon_name in ["play", "pause", "resume", "infinity", "menu"]:
    icon = pygame.image.load(os.path.join("icons", icon_name + ".png")).convert_alpha()
    icon = pygame.transform.smoothscale(icon, (BUTTON_SIZE, BUTTON_SIZE))
    icons[icon_name] = icon
icon = pygame.image.load(os.path.join("icons", "infinity.png")).convert_alpha()
icon = pygame.transform.smoothscale(icon, (BUTTON_SIZE, BUTTON_SIZE))
icon.set_alpha(100)
icons["no_infinity"] = icon

############# BUTTONS #####################
pause_button = pygame.Rect((SCREEN_WIDTH - BAR_MARGIN - (4 * BUTTON_SIZE)), BAR_Y_POS, BUTTON_SIZE, BUTTON_SIZE)
autoplay_button = pygame.Rect((SCREEN_WIDTH - BAR_MARGIN - (2.5 * BUTTON_SIZE)), BAR_Y_POS, BUTTON_SIZE, BUTTON_SIZE)



################### DEFAULTS ###########################





class Status:

    # default constructor
    def __init__(self):
        self.running = True
        self.autoplay = False
        self.done = False
        self.paused = True

        self.current_depth = 1
        self.image = None
        self.states = [State(0, -1, np.pi / 2, 1, 4)]

        plt.figure(figsize=(9, 8))
        plt.axis('off')
        ax = plt.gca()
        ax.set_xlim([-2.5, 2.5])
        ax.set_ylim([-1, 2.8])

    def restart(self):
        self.done = False

        self.current_depth = 1
        self.image = None
        self.states = [State(0, -1, np.pi / 2, 1, 4)]
        plt.clf()
        plt.figure(figsize=(9, 8))
        plt.axis('off')
        ax = plt.gca()
        ax.set_xlim([-2.5, 2.5])
        ax.set_ylim([-1, 2.8])

    def load_image(self, path):
        self.image = pygame.image.load(path)
        #self.image = pygame.transform.smoothscale(self.image, (LEFT_WIDTH - 2*TREE_MARGIN, LEFT_WIDTH - 2 * TREE_MARGIN))





############################## MAIN LOOP ##################################


s = Status()
clock = pygame.time.Clock()
init_dir()
refresh(screen, s)
while s.running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            s.running = False
        if event.type == pygame.MOUSEBUTTONUP:
            pos = pygame.mouse.get_pos()
            if pause_button.collidepoint(pos):
                r = pygame.draw.rect(screen, (255, 255, 255), pause_button)
                if s.done:
                    # restart
                    screen.blit(icons["pause"], icons["pause"].get_rect(center = pause_button.center))
                    s.restart()
                    s.paused = False
                elif s.paused:
                    # play
                    screen.blit(icons["pause"], icons["pause"].get_rect(center = pause_button.center))
                    s.paused = False
                else:
                    # pause
                    screen.blit(icons["play"], icons["play"].get_rect(center = pause_button.center))
                    s.paused = True
                pygame.display.update(r)
            if autoplay_button.collidepoint(pos):
                # autoplay toggle
                r = pygame.draw.rect(screen, (255, 255, 255), autoplay_button)
                if s.autoplay:
                    screen.blit(icons["no_infinity"], icons["no_infinity"].get_rect(center = autoplay_button.center))
                    s.autoplay = False
                else:
                    screen.blit(icons["infinity"], icons["infinity"].get_rect(center = autoplay_button.center))
                    s.autoplay = True
                pygame.display.update(r)

    if not s.paused and not s.done:
        if s.current_depth == 16:
            if s.autoplay:
                refresh(screen, s)
                #restart
                r = pygame.draw.rect(screen, (255, 255, 255), pause_button)
                screen.blit(icons["pause"], icons["pause"].get_rect(center = pause_button.center))
                pygame.display.update(r)
                s.restart()
                s.paused = False
            else:
                #show final screen
                s.done = True
                s.paused = True
                refresh(screen, s)
        else:

            new_states = []
            for state in s.states:
                new_x = state.x + state.length * np.cos(state.angle)
                new_y = state.y + state.length * np.sin(state.angle)
                plt.plot([state.x, new_x], [state.y, new_y], 'black', lw=state.width)
                new_states.append(State(new_x, new_y, state.angle + ANGLE_OFFSET, state.length * 0.75, state.width * 0.75))
                new_states.append(State(new_x, new_y, state.angle - ANGLE_OFFSET, state.length * 0.75, state.width * 0.75))
            plt.savefig("temp/tree.png")
            s.states = new_states
            s.current_depth += 1
            s.load_image(os.path.join("temp", "tree.png"))
            refresh(screen, s)


    clock.tick(60)

if os.path.isdir("temp"):
    shutil.rmtree("temp")
pygame.quit()
