import pygame
import os
import shutil
import math
import time

from ete3 import Tree
from ete3.treeview import faces, TreeStyle
from PIL import Image, ImageOps


import numpy as np
import pygame_menu as pm

################### TREE DRAWING ############################################################
def height(tree):
    return max(leaf_depths(tree))

def depths_in_subtree(node, depth):
    depths_below = []
    for child in node.children:
        if child.is_leaf():
            depths_below.append(depth + 1)
        else:
            depths_below += depths_in_subtree(child, depth + 1)
    return depths_below

def leaf_depths(tree):
    return depths_in_subtree(tree, 0)

def fancy(node, example):
    # If node is a leaf, add the nodes name and a its scientific
    # name
    if node.is_leaf():
        faces.add_face_to_node(faces.ImgFace(os.path.join("imgs", example, node.name + ".png")), node, column=0)
    #node.img_style["size"] = 50
    #node.img_style["shape"] = "circle"
    #node.img_style["fgcolor"] = "#000000"
    node.img_style["hz_line_width"] = 10
    node.img_style["vt_line_width"] = 10

def pictogram(node):
    node.img_style["size"] = 0
    node.img_style["shape"] = "circle"
    node.img_style["fgcolor"] = "#000000"
    node.img_style["hz_line_width"] = 2
    node.img_style["vt_line_width"] = 2


def resize_with_padding(path, expected_size):
    img = Image.open(path)
    delta_width = expected_size - img.size[0]
    delta_height = expected_size - img.size[1]
    pad_width = delta_width // 2
    pad_height = delta_height // 2
    padding = (pad_width, pad_height, delta_width - pad_width, delta_height - pad_height)
    img = ImageOps.expand(img, padding, fill = (255, 255, 255))
    img.save(path)


def draw_tree(path, example):
    t = Tree(path)
    ts = TreeStyle()
    ts.layout_fn = lambda node : fancy(node, example)
    ts.show_leaf_name = False
    ts.show_scale = False
    ts.scale = (2000 * 8) / height(t)
    ts.branch_vertical_margin = 50
    path = os.path.join("temp", "tree.png")
    t.render(path, w=2000, tree_style = ts)
    resize_with_padding(path, 2500)

    ts = TreeStyle()
    ts.layout_fn = pictogram
    ts.show_leaf_name = False
    ts.show_scale = False
    ts.scale = (200 * 8) / height(t)
    ts.branch_vertical_margin = 10
    path = os.path.join("temp", "thumbnail.png")
    t.render(path, w=180, tree_style = ts)
    resize_with_padding(path, 200)



######################## UI FUNCTIONS ##################################


def draw_thumbnails(screen, s):
    max_thumbs_in_col = (SCREEN_HEIGHT - THUMB_MARGIN) // (THUMB_SIZE[1] + THUMB_MARGIN)
    r = math.ceil(math.sqrt(s.num_trees))

    for i in range(s.num_trees):
        row = i % r
        col = i // r
        x_pos = LEFT_WIDTH + col * (THUMB_SIZE[0] + THUMB_MARGIN) + THUMB_MARGIN
        y_pos = row * (THUMB_SIZE[1] + THUMB_MARGIN) + THUMB_MARGIN
        if i < len(s.thumbnails):
            thumbnail = s.thumbnails[i]
            screen.blit(thumbnail, (x_pos, y_pos))
            if i == s.best_index:
                color = GREEN_COLOR
            else:
                color = (0, 0, 0)
        else:
            color = (180, 180, 180)
        pygame.draw.rect(screen, color, (x_pos - 2, y_pos - 2, THUMB_SIZE[0] + 4, THUMB_SIZE[1] + 4), 2)

def to_string(num):
    if num != num:
        return ""
    else:
        return str(round(num, 1))

def draw_bar(screen, s):
    cursor = BAR_MARGIN
    text_surface = font.render("Best score: " + to_string(s.best_llh), True, GREEN_COLOR)
    screen.blit(text_surface, (cursor, BAR_Y_POS))
    cursor += font.size("Best score: 10000000")[0]
    if not s.done:
        text_surface = font.render("Current score: " + to_string(s.llh), True, (0, 0, 0))
        screen.blit(text_surface, (cursor, BAR_Y_POS))
        cursor += font.size("Current score: 10000000")[0]
        text_surface = font.render("Trees per Second: " + to_string(s.tps), True, (0, 0, 0))
        screen.blit(text_surface, (cursor, BAR_Y_POS))


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
    pygame.draw.rect(screen, (255, 255, 255), menu_button)
    screen.blit(icons["menu"], icons["menu"].get_rect(center = menu_button.center))


######################### DATA SETTINGS #######################################

all_examples = [("Animals", "animal"), ("Languages", "language"), ("Horses", "horse")]
models = {"language" : "BIN+G", "animal" : "GTR+G", "horse" : "GTR+G"}


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


def get_thumb_sizes(num_trees):
    r = math.ceil(math.sqrt(num_trees))
    thumb_full_size = int(RIGHT_WIDTH / r)
    ts = int(thumb_full_size * 0.8)
    return (ts, ts), thumb_full_size - ts



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
menu_button = pygame.Rect((SCREEN_WIDTH - BAR_MARGIN - BUTTON_SIZE), BAR_Y_POS, BUTTON_SIZE, BUTTON_SIZE)

################### MENU #############################
def close_menu():
    settings.disable()

theme = pm.Theme(widget_font=font, widget_margin = (SCREEN_WIDTH*0.08, 0.0))
settings = pm.Menu(title="Settings", width=SCREEN_WIDTH*0.8, height=SCREEN_HEIGHT*0.8, theme = theme)
settings._theme.widget_font_color = (0, 0, 0)
settings._theme.widget_alignment = pm.locals.ALIGN_LEFT


settings.add.dropselect(title="Example:", items=all_examples, default = 0, dropselect_id="example")
settings.add.dropselect(title="Tree Mode:", items=[("Random", "rand"), ("Parsimony", "pars")], default = 0, dropselect_id="tree_mode")
settings.add.range_slider(title="Number of Trees:", default=100, range_values=(9, 900), increment=1, value_format=lambda x: str(int(x)), rangeslider_id="num_trees")
settings.add.button(title="START", action=close_menu, button_id = "start")
settings.select_widget("start")



################### DEFAULTS ###########################





class Status:

    # default constructor
    def __init__(self):
        self.running = True
        self.autoplay = False
        self.done = False
        self.paused = True

        self.example = ""
        self.tree_mode = ""
        self.num_trees = float("nan")

        self.current_index = 0
        self.best_index = -1
        self.best_image = None
        self.tps = float("nan")
        self.best_llh = float("nan")
        self.llh = float("nan")

        self.image = None
        self.thumbnails = []

    def set_input_data(self, new_data):
        changed = False
        new_data = settings.get_input_data()
        if new_data["example"][0][1] != self.example:
            self.example = new_data["example"][0][1]
            changed = True
        if new_data["tree_mode"][0][1] != self.tree_mode:
            self.tree_mode = new_data["tree_mode"][0][1]
            changed = True
        if new_data["num_trees"] != self.num_trees:
            self.num_trees = int(new_data["num_trees"])
            changed = True
        return changed

    def restart(self):
        self.done = False

        self.current_index = 0
        self.best_index = -1
        self.best_image = None
        self.tps = float("nan")
        self.best_llh = float("nan")
        self.llh = float("nan")
        self.image = None
        self.thumbnails = []

    def load_image(self, path):
        self.image = pygame.image.load(path)
        self.image = pygame.transform.smoothscale(self.image, (LEFT_WIDTH - 2*THUMB_MARGIN, LEFT_WIDTH - 2 * THUMB_MARGIN))

    def update_llh(self, llh):
        self.llh = llh
        if self.best_llh != self.best_llh or llh > self.best_llh:
            self.best_llh = llh
            self.best_index = self.current_index
            self.best_image = self.image

    def load_thumbnail(self, path):
        new_thumbnail = pygame.image.load(path)
        new_thumbnail = pygame.transform.smoothscale(new_thumbnail, THUMB_SIZE)
        self.thumbnails.append(new_thumbnail)




s = Status()



############################## MAIN LOOP ##################################

while s.running:
    if s.example == "": #open menu at the beginning
        settings.mainloop(screen)
        s.set_input_data(settings.get_input_data())
        init_dir()

        screen.fill((255, 255, 255))
        THUMB_SIZE, THUMB_MARGIN = get_thumb_sizes(s.num_trees)
        draw_thumbnails(screen, s)
        draw_bar(screen, s)
        pygame.display.flip()

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
            if menu_button.collidepoint(pos):
                settings.enable()
                settings.mainloop(screen)
                changed = s.set_input_data(settings.get_input_data())
                if changed:
                    init_dir()
                    s.restart()
                    s.paused = True
                    screen.fill((255, 255, 255))
                    THUMB_SIZE, THUMB_MARGIN = get_thumb_sizes(s.num_trees)
                else:
                    # paused after settings call
                    s.paused = True
                    screen.fill((255, 255, 255))
                    if s.image is not None:
                        screen.blit(s.image, (THUMB_MARGIN, THUMB_MARGIN))
                draw_thumbnails(screen, s)
                draw_bar(screen, s)
                pygame.display.flip()

    if not s.paused and not s.done:
        if s.current_index == s.num_trees:
            if s.autoplay:
                screen.fill((255, 255, 255))
                screen.blit(s.image, (0, 0))
                draw_thumbnails(screen, s)
                draw_bar(screen, s)
                pygame.display.flip()
                #restart
                r = pygame.draw.rect(screen, (255, 255, 255), pause_button)
                screen.blit(icons["pause"], icons["pause"].get_rect(center = pause_button.center))
                pygame.display.update(r)
                s.restart()
                s.paused = False
            else:
                #show final screen
                s.done = True
                screen.fill((255, 255, 255))
                screen.blit(s.best_image, (THUMB_MARGIN, THUMB_MARGIN))
                pygame.draw.rect(
                    screen,
                    GREEN_COLOR,
                    (THUMB_MARGIN, THUMB_MARGIN, LEFT_WIDTH - 2 * THUMB_MARGIN, LEFT_WIDTH - 2 * THUMB_MARGIN),
                    2  # Border thickness
                    )
                draw_thumbnails(screen, s)
                draw_bar(screen, s)
                pygame.display.flip()
        else:

            #generate tree
            command = "./raxml-ng "
            command += " --tree " + s.tree_mode + "{1}"
            command += " --model " + models[s.example]
            command += " --msa " + os.path.join("msa", s.example + ".phy")
            command += " --prefix " + os.path.join("temp", "generate")
            command += " --seed " + str(s.current_index)
            command += " --threads auto --redo > " + os.path.join("temp", "out.txt")
            t0 = time.time()
            os.system(command)
            t1 = time.time()

            #draw tree
            draw_tree(os.path.join("temp", "generate.raxml.startTree"), s.example)
            s.load_image(os.path.join("temp", "tree.png"))
            screen.fill((255, 255, 255))
            screen.blit(s.image, (THUMB_MARGIN, THUMB_MARGIN))
            draw_thumbnails(screen, s)
            draw_bar(screen, s)
            pygame.display.flip()


            #evaluate tree
            command = "./raxml-ng --evaluate "
            command += " --msa " + os.path.join("msa", s.example + ".phy")
            command += " --tree " + os.path.join("temp", "generate.raxml.bestTree")
            command += " --model " + models[s.example]
            command += " --prefix " + os.path.join("temp", "evaluate")
            command += " --seed 2 --threads auto --redo > " + os.path.join("temp", "out.txt")
            t2 = time.time()
            os.system(command)
            t3 = time.time()

            #execution_time = (t1 - t0) + (t3 - t2) #depends on what you want to measure
            execution_time = t3 - t0
            s.tps = 1.0 / execution_time

            with open(os.path.join("temp", "evaluate.raxml.log"), "r") as logfile:
                lines = logfile.readlines()
            llh = float("nan")
            for line in lines:
                if line.startswith("Final LogLikelihood: "):
                    llh = float(line.split(": ")[1])
                    break
            s.update_llh(llh)


            #update thumbnails
            s.load_thumbnail(os.path.join("temp", "thumbnail.png"))
            s.current_index = s.current_index + 1

if os.path.isdir("temp"):
    shutil.rmtree("temp")
pygame.quit()
