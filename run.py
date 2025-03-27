import pygame
import os
import shutil
import math
import time

from PIL import Image, ImageOps


import numpy as np
import pygame_menu as pm
import matplotlib as mpl
import matplotlib.pyplot as plt

################### TREE DRAWING ############################################################

ON = 255
OFF = 0


def update_gol(gol_img, grid, H, W):
    newGrid = grid.copy()
    for i in range(H):
        for j in range(W):
            total = int((grid[i, (j-1)%W] + grid[i, (j+1)%W] +
                grid[(i-1)%H, j] + grid[(i+1)%H, j] +
                grid[(i-1)%H, (j-1)%W] + grid[(i-1)%H, (j+1)%W] +
                grid[(i+1)%H, (j-1)%W] + grid[(i+1)%H, (j+1)%W])/255)
			# apply Conway's rules
            if grid[i, j] == ON:
                if (total < 2) or (total > 3):
                    newGrid[i, j] = OFF
            else:
                if total == 3:
                    newGrid[i, j] = ON

	# update data
    gol_img.set_data(newGrid)
    grid[:] = newGrid[:]
    plt.savefig("temp/tree.png", bbox_inches='tight', pad_inches=0,  dpi = 190)



######################## UI FUNCTIONS ##################################


def draw_bar(screen, s):
    cursor = BAR_MARGIN
    text_surface = font.render("Generations per Second: " + to_string(s.gps), True, (0, 0, 0))
    screen.blit(text_surface, (cursor, BAR_Y_POS))
    pygame.draw.rect(screen, (255, 255, 255), resume_button)
    screen.blit(icons["resume"], icons["resume"].get_rect(center = resume_button.center))


def refresh(screen, s):
    screen.fill((255, 255, 255))
    if s.image is not None:
        screen.blit(s.image, (MARGIN, MARGIN))
    draw_bar(screen, s)
    pygame.display.flip()



def to_string(num):
    if num != num:
        return ""
    else:
        return str(round(num, 1))


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
MARGIN = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.05)
BAR_HEIGHT = int(SCREEN_HEIGHT * 0.2 * 0.8)
BAR_MARGIN = int(SCREEN_HEIGHT * 0.2 * 0.2)
BAR_Y_POS = SCREEN_HEIGHT - BAR_HEIGHT + BAR_MARGIN*0.5

BUTTON_SIZE = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) / 20)
IMG_WIDTH = SCREEN_WIDTH - 2 * MARGIN
IMG_HEIGHT = SCREEN_HEIGHT - 2 * MARGIN - BAR_HEIGHT

pygame.font.init()
font = pygame.font.Font(os.path.join("fonts", 'MiriamLibre-Regular.ttf'), 30)


icons = {}
for icon_name in ["resume"]:
    icon = pygame.image.load(os.path.join("icons", icon_name + ".png")).convert_alpha()
    icon = pygame.transform.smoothscale(icon, (BUTTON_SIZE, BUTTON_SIZE))
    icons[icon_name] = icon

resume_button = pygame.Rect((SCREEN_WIDTH - BAR_MARGIN - BUTTON_SIZE), BAR_Y_POS, BUTTON_SIZE, BUTTON_SIZE)







class Status:

    # default constructor
    def __init__(self):
        self.running = True
        self.gps = float("nan")

        self.image = None
        self.W = int(IMG_WIDTH / 5)
        self.H = int(IMG_HEIGHT / 5)
        self.grid = np.random.choice([ON, OFF], self.H*self.W, p=[0.2, 0.8]).reshape(self.H, self.W)
        mpl.rcParams[ 'figure.figsize' ] = (IMG_WIDTH  // 128, IMG_HEIGHT // 128)
        #mpl.rcParams[ 'figure.dpi' ] = 128
        fig, ax = plt.subplots()
        plt.axis('off')
        fig.set_size_inches(IMG_WIDTH  // 128, IMG_HEIGHT // 128)
        self.gol_img = ax.imshow(self.grid, interpolation='nearest', cmap = 'inferno')


    def load_image(self, path):
        self.image = pygame.image.load(path)
        #self.image = pygame.transform.smoothscale(self.image, (LEFT_WIDTH - 2*TREE_MARGIN, LEFT_WIDTH - 2 * TREE_MARGIN))

    def restart(self):
        self.grid = np.random.choice([ON, OFF], self.H*self.W, p=[0.2, 0.8]).reshape(self.H, self.W)






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
            if resume_button.collidepoint(pos):
                s.restart()
    t_0 = time.time()
    update_gol(s.gol_img, s.grid, s.H, s.W)
    t_1 = time.time()
    s.load_image(os.path.join("temp", "tree.png"))
    s.gps = 1.0 / (t_1 - t_0)
    refresh(screen, s)


    #clock.tick(60)

if os.path.isdir("temp"):
    shutil.rmtree("temp")
pygame.quit()
