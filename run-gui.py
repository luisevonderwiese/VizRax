#!/usr/bin/env python3

import pygame
import os
import shutil
import math
import time
import argparse

from ete3 import Tree
from ete3.treeview import faces, TreeStyle
from PIL import Image, ImageOps

import json
import asyncio
from aiomqtt import Client, MqttError

import numpy as np
import pygame_menu as pm

from PyQt5.QtGui import QImage

orig_qimage_save = QImage.save

def new_save(self, fileName, format=None, quality=None):
#  print("monkey patched!")
  if not quality:
    quality = 100
  orig_qimage_save(self, fileName, format, quality)

QImage.save = new_save

#temp_dir="temp"
temp_dir="/dev/shm/rxviz-temp"
example_faces = {}

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
#        faces.add_face_to_node(example_faces[node.name], node, column=0)
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


def draw_tree(newick, example, s):
    t = Tree(newick)
    ts = TreeStyle()
    ts.layout_fn = lambda node : fancy(node, example)
    ts.show_leaf_name = False
    ts.show_scale = False
    ts.force_topology = True
    TREE_PNG_SIZE = min(SCREEN_WIDTH, TREE_HEIGHT) * 0.9
    ts.scale = (TREE_PNG_SIZE * 1) / height(t)
    ts.branch_vertical_margin = 50
    path = os.path.join(temp_dir, "tree.png")
    tt1 = time.time()
    t.render(path, w=TREE_PNG_SIZE, h=TREE_PNG_SIZE, tree_style = ts)
    tt2 = time.time()
#    print ("render time: ", tt2 - tt1)
#    resize_with_padding(path, 2500)

    ts = TreeStyle()
    ts.layout_fn = pictogram
    ts.show_leaf_name = False
    ts.show_scale = False
    ts.force_topology = True
    ts.scale = (s.thumb_size[0] * 1) / height(t)
    ts.branch_vertical_margin = 10
    ts.margin_left = ts.margin_right = ts.margin_top = ts.margin_bottom = 10
    path = os.path.join(temp_dir, "thumbnail.png")
#    t.render(path, w=200, tree_style = ts)
    t.render(path, w=s.thumb_size[0], h=s.thumb_size[1],  tree_style = ts)
#    resize_with_padding(path, 200)



######################## UI FUNCTIONS ##################################

def draw_msa(screen, s):
    msa_image = pygame.image.load(os.path.join("msa_plots", "animal.png"))
    msa_image = pygame.transform.smoothscale(msa_image, (MSA_WIDTH - 2 * MSA_MARGIN, MSA_HEIGHT - 2 * MSA_MARGIN))
    screen.blit(msa_image, (MSA_MARGIN + MSA_ICON_SIZE, MSA_MARGIN))
    for i, icon in enumerate(["Frog", "Turtle", "Bird", "Human", "Cow", "Whale", "Mouse"]):
        icon_image = pygame.image.load(os.path.join("imgs/animal", icon + ".png"))
        icon_image = pygame.transform.smoothscale(icon_image, (MSA_ICON_SIZE * 0.8, MSA_ICON_SIZE * 0.8))
        screen.blit(icon_image, (MSA_MARGIN + MSA_ICON_SIZE * 0.1, MSA_MARGIN + (i + 0.1) * MSA_ICON_SIZE))

def draw_thumbnails(screen, s):
    for i in range(s.num_trees):
        row = i // THUMBS_IN_A_ROW
        col = i - row * THUMBS_IN_A_ROW
        x_pos = s.tn_xpos_offset + col * (s.thumb_size[0] + s.thumb_margin) + s.thumb_margin / 2
        y_pos = s.tn_ypos_offset + row * (s.thumb_size[1] + s.thumb_margin) + s.thumb_margin / 2
        if i < len(s.thumbnails):
            thumbnail = s.thumbnails[i]
            screen.blit(thumbnail, (x_pos, y_pos))
            if i == s.best_index:
                color = GREEN_COLOR
            else:
                color = (0, 0, 0)
        else:
            color = (180, 180, 180)
        pygame.draw.rect(screen, color, (x_pos - 2, y_pos - 2, s.thumb_size[0] + 4, s.thumb_size[1] + 4), 2)

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
        tps = s.tps
    else:
        tps = s.num_trees / s.time
    text_surface = font.render("Trees per Second: " + to_string(s.tps), True, (0, 0, 0))
    screen.blit(text_surface, (cursor, BAR_Y_POS))
    cursor += font.size("Trees per Second: 10.000")[0]
    text_surface = font.render("Time: " + to_string(s.time), True, (0, 0, 0))
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
#    pygame.draw.rect(screen, (255, 255, 255), menu_button)
#    screen.blit(icons["menu"], icons["menu"].get_rect(center = menu_button.center))


def refresh(screen, s):
    screen.fill((255, 255, 255))
    if s.image is not None:
        screen.blit(s.image, (s.tree_xpos, s.tree_ypos))
    draw_thumbnails(screen, s)
    draw_bar(screen, s)
    draw_msa(screen, s)
    pygame.display.flip()

def final_screen(screen, s):
    screen.fill((255, 255, 255))
    screen.blit(s.best_image, (s.tree_xpos, s.tree_ypos))
    size = min(SCREEN_WIDTH, TREE_HEIGHT) - 2 * TREE_MARGIN
    pygame.draw.rect(
        screen,
        GREEN_COLOR,
        (s.tree_xpos, s.tree_ypos, size, size),
        2  # Border thickness
    )
    draw_thumbnails(screen, s)
    draw_bar(screen, s)
    draw_msa(screen, s)
    pygame.display.flip()


######################### DATA SETTINGS #######################################

all_examples = [("Animals", "animal"), ("Languages", "language"), ("Horses", "horse")]
models = {"language" : "BIN+G", "animal" : "GTR+G", "horse" : "GTR+G"}



def init_dir():
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

def init_config():
    parser = argparse.ArgumentParser(description="VizRax frontend")
    parser.add_argument("--broker", type=str, default="localhost", dest="mqtt_host", help="Address of the MQTT server")
    parser.add_argument("--width", type=int, default=argparse.SUPPRESS, help="Screen width in pixels")
    parser.add_argument("--height", type=int, default=argparse.SUPPRESS, help="Screen height in pixels")
    parser.add_argument("--nomenu", dest="showmenu", action="store_false", help="Do not show Settings dialog before start")
    args = parser.parse_args()

    cfg = vars(args)
#    cfg["mqtt_host"] = args.broker
    return cfg





######################### SIZES ##################################################
pygame.init()
infoObject = pygame.display.Info()

#SCREEN_WIDTH = 1700
#SCREEN_HEIGHT = infoObject.current_h

#screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h), pygame.RESIZABLE)
#screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)

pygame.display.set_caption("VizRax")
icon = pygame.image.load(os.path.join("icons", "horse.png"))
pygame.display.set_icon(icon)



################### MENU #############################
def close_menu():
    settings.disable()

def init_pygame(cfg):

    ######################### SIZES ##################################################
    pygame.init()
    infoObject = pygame.display.Info()

    print(cfg)
    global SCREEN_WIDTH, SCREEN_HEIGHT
    SCREEN_WIDTH = cfg.get("width", infoObject.current_w)
    SCREEN_HEIGHT = cfg.get("height", infoObject.current_h)

    global screen
    #screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h), pygame.RESIZABLE)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)

    pygame.display.set_caption("VizRax")
    icon = pygame.image.load(os.path.join("icons", "horse.png"))
    pygame.display.set_icon(icon)

    global BAR_HEIGHT, BAR_MARGIN, BAR_Y_POS, BUTTON_SIZE
    BAR_HEIGHT = int(SCREEN_HEIGHT * 0.2 * 0.8)
    BAR_MARGIN = int(SCREEN_HEIGHT * 0.2 * 0.2)
    BAR_Y_POS = SCREEN_HEIGHT - BAR_HEIGHT + BAR_MARGIN * 0.5
    BUTTON_SIZE = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) / 20)

    global MSA_HEIGHT, MSA_MARGIN, MSA_ICON_SIZE, MSA_WIDTH
    MSA_HEIGHT = SCREEN_HEIGHT // 4
    MSA_MARGIN = SCREEN_WIDTH * 0.01
    MSA_ICON_SIZE = (MSA_HEIGHT - (2 * MSA_MARGIN)) // 7
    MSA_WIDTH = SCREEN_WIDTH - MSA_ICON_SIZE


    global THUMBNAIL_HEIGHT, THUMBNAIL_MARGIN, THUMBS_IN_A_ROW, THUMBS_IN_A_COL
    THUMBNAIL_HEIGHT = SCREEN_HEIGHT // 4
    THUMBNAIL_MARGIN = SCREEN_WIDTH * 0.01
    THUMBS_IN_A_ROW = 20
    THUMBS_IN_A_COL = 5

    global TREE_HEIGHT, TREE_MARGIN
    TREE_HEIGHT = SCREEN_HEIGHT - BAR_HEIGHT - MSA_HEIGHT - THUMBNAIL_HEIGHT
    TREE_MARGIN = min(SCREEN_WIDTH, TREE_HEIGHT) * 0.05


    #################### COLORS ####################
    global GREEN_COLOR
    GREEN_COLOR = (0, 180, 0)  # Green color for the box around thumbnails

    ################## FONTS ######################################
    global font
    pygame.font.init()
    font = pygame.font.Font(os.path.join("fonts", 'MiriamLibre-Regular.ttf'), 30)



    ################# ICONS #################################
    global icons
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
    global pause_button, autoplay_button, menu_button
    pause_button = pygame.Rect((SCREEN_WIDTH - BAR_MARGIN - (4 * BUTTON_SIZE)), BAR_Y_POS, BUTTON_SIZE, BUTTON_SIZE)
    autoplay_button = pygame.Rect((SCREEN_WIDTH - BAR_MARGIN - (2.5 * BUTTON_SIZE)), BAR_Y_POS, BUTTON_SIZE, BUTTON_SIZE)
    menu_button = pygame.Rect((SCREEN_WIDTH - BAR_MARGIN - BUTTON_SIZE), BAR_Y_POS, BUTTON_SIZE, BUTTON_SIZE)

    ################### MENU #############################
    theme = pm.Theme(widget_font=font, widget_margin = (SCREEN_WIDTH*0.08, 0.0))
    global settings
    settings = pm.Menu(title="Settings", width=SCREEN_WIDTH*0.8, height=SCREEN_HEIGHT*0.8, theme = theme)
    settings._theme.widget_font_color = (0, 0, 0)
    settings._theme.widget_alignment = pm.locals.ALIGN_LEFT


    settings.add.dropselect(title="Example:", items=all_examples, default = 0, dropselect_id="example")
    settings.add.dropselect(title="Tree Mode:", items=[("Random", "rand"), ("Parsimony", "pars")], default = 1, dropselect_id="tree_mode")
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
        self.tree = ""
        self.num_trees = float("nan")

        self.current_index = 0
        self.best_index = -1
        self.best_image = None
        self.tps = float("nan")
        self.best_llh = float("nan")
        self.llh = float("nan")
        self.time = 0

        self.image = None
        self.thumbnails = []

        self.thumb_size = float("nan")
        self.thumb_margin = float("nan")
        if SCREEN_WIDTH > TREE_HEIGHT:
            self.tree_xpos = TREE_MARGIN + (SCREEN_WIDTH - TREE_HEIGHT) / 2
            self.tree_ypos = MSA_HEIGHT + TREE_MARGIN
        else:
            self.tree_xpos = TREE_MARGIN
            self.tree_ypos = MSA_HEIGHT + TREE_MARGIN + (TREE_HEIGHT - SCREEN_WIDTH) / 2

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
            thumb_full_size = int(min((SCREEN_WIDTH - 2 * THUMBNAIL_MARGIN) / THUMBS_IN_A_ROW, (THUMBNAIL_HEIGHT - 2 * THUMBNAIL_MARGIN) / (THUMBS_IN_A_COL)))
            ts = int(thumb_full_size * 0.8)
            self.thumb_size = (ts, ts)
            self.thumb_margin = thumb_full_size - ts
            self.tn_xpos_offset = (SCREEN_WIDTH - (THUMBS_IN_A_ROW * thumb_full_size)) / 2
            self.tn_ypos_offset = MSA_HEIGHT + TREE_HEIGHT + (THUMBNAIL_HEIGHT - (THUMBS_IN_A_COL * thumb_full_size)) / 2
            changed = True
        return changed

    def get_input_data(self):
      data = {"example": self.example, "tree_mode": self.tree_mode, "num_trees": self.num_trees }
      return data

    def restart(self):
        self.done = False

        self.current_index = 0
        self.time = 0
        self.best_index = -1
        self.best_image = None
        self.tps = float("nan")
        self.best_llh = float("nan")
        self.llh = float("nan")
        self.image = None
        self.thumbnails = []

    def load_image(self, path):
        self.image = pygame.image.load(path)
        size = min(SCREEN_WIDTH, TREE_HEIGHT) - 2 * TREE_MARGIN
        self.image = pygame.transform.smoothscale(self.image, (size, size))
        if self.best_index == self.current_index:
            self.best_image = self.image

    def update_llh(self, llh):
        self.llh = llh
        if self.best_llh != self.best_llh or llh > self.best_llh:
            self.best_llh = llh
            self.best_index = self.current_index

    def update_from_msg(self, msg):
        self.tree = msg["tree"]
        self.tps = msg["tps"]
        self.time += 1.0 / self.tps
        llh = msg["llh"]
        self.update_llh(llh)

    def load_thumbnail(self, path):
        new_thumbnail = pygame.image.load(path)
#        new_thumbnail = pygame.transform.smoothscale(new_thumbnail, self.thumb_size)
        self.thumbnails.append(new_thumbnail)


############################## MQTT ##################################

class MQTTClient(object):
  recv_queue: asyncio.Queue
  send_queue: asyncio.Queue

  def __init__(self, config):
    self.hostname = config.get("mqtt_host", "localhost")
    self.port = config.get("mqtt_port", 1883)
    self.username = config.get("mqtt_user", None)
    self.password = config.get("mqtt_password", None)
    self.sub_topic = config.get("upd_topic", "raxviz/status")
    self.pub_topic = config.get("cmd_topic", "raxviz/command")
    self.pub_fields = config.get("pubfields", None)
    if self.pub_fields:
      self.pub_fields = self.pub_fields.split(",")

  async def spin(self):
    self.recv_queue = asyncio.Queue()
    self.send_queue = asyncio.Queue()
    while True:
      print('Connecting to MQTT broker...')
      try:
          async with Client(
              hostname=self.hostname,
              port=self.port,
              username=self.username,
              password=self.password
          ) as client:
              print('Connected to MQTT broker')

              # Handle pub/sub
              await asyncio.gather(
                  self.handle_sub(client),
                  self.handle_pub(client)
              )
      except MqttError:
          print('MQTT error:')
          await asyncio.sleep(5)

  async def handle_sub(self, client):
    if not self.sub_topic:
      return
    await client.subscribe(self.sub_topic)
    async for message in client.messages:
      data = json.loads(message.payload)
      self.recv_queue.put_nowait(data)

  async def handle_pub(self, client):
    if not self.pub_topic:
      return
    while True:
      data = await self.send_queue.get()
      payload = json.dumps(data)
      print(payload)
      await client.publish(self.pub_topic, payload=payload.encode())
      self.send_queue.task_done()

  def get_msg(self):
    try:
      return self.recv_queue.get_nowait()
    except asyncio.queues.QueueEmpty:
      return None

  def put_msg(self, data):
    if self.pub_fields:
      data = {key: data[key] for key in self.pub_fields}
    self.send_queue.put_nowait(data)


############################## MAIN LOOP ##################################

def run_once(loop):
    loop.call_soon(loop.stop)
    loop.run_forever()

def mqtt_settings(loop, mqtt, s):
    stgs = s.get_input_data()
    stgs["cmd"] = "settings"
#    print(stgs)
    mqtt.put_msg(stgs)
    run_once(loop)


def main(cfg):
    s = Status()
    clock = pygame.time.Clock()
    example_names = ["Frog", "Turtle", "Bird", "Human", "Cow", "Whale", "Mouse"]

    mqtt = MQTTClient(cfg)

    loop = asyncio.new_event_loop()
    t1 = loop.create_task(mqtt.spin())
    run_once(loop)

    if s.example == "": #open menu at the beginning
        if cfg["showmenu"]:
          settings.mainloop(screen)
        s.set_input_data(settings.get_input_data())
        mqtt_settings(loop, mqtt, s)
        init_dir()

        for name in example_names:
          example_faces[name] = faces.ImgFace(os.path.join("imgs", s.example, name + ".png"))

        refresh(screen, s)

    mqtt.put_msg({"cmd": "restart"})

    # Enable infinite autoplay by default
    s.autoplay = True
    screen.blit(icons["infinity"], icons["infinity"].get_rect(center = autoplay_button.center))

    while s.running:
        run_once(loop)
        clock.tick(60)

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
                        mqtt.put_msg({"cmd": "restart"})
                    elif s.paused:
                        # play
                        screen.blit(icons["pause"], icons["pause"].get_rect(center = pause_button.center))
                        s.paused = False
                        mqtt.put_msg({"cmd": "start"})
                    else:
                        # pause
                        screen.blit(icons["play"], icons["play"].get_rect(center = pause_button.center))
                        s.paused = True
                        mqtt.put_msg({"cmd": "pause"})
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
                        mqtt_settings(loop, mqtt, s)
                        init_dir()
                        s.restart()
                    s.paused = True
                    refresh(screen, s)

        if not s.paused and not s.done:
            if s.current_index == s.num_trees:
                if s.autoplay:
                    refresh(screen, s)
                    #restart
                    r = pygame.draw.rect(screen, (255, 255, 255), pause_button)
                    screen.blit(icons["pause"], icons["pause"].get_rect(center = pause_button.center))
                    pygame.display.update(r)
                    s.restart()
                    s.paused = False
                    mqtt.put_msg({"cmd": "restart"})
                else:
                    #show final screen
                    s.done = True
                    final_screen(screen, s)

            else:
                msg = mqtt.get_msg()

                if not msg:
                  continue

#                 print(msg)

                s.update_from_msg(msg)

#                execution_time = tt2 - tt1

                #draw tree
                tt1 = time.time()
                draw_tree(s.tree, s.example, s)
                s.load_image(os.path.join(temp_dir, "tree.png"))
                refresh(screen, s)
                tt2 = time.time()

                #update thumbnails
                s.load_thumbnail(os.path.join(temp_dir, "thumbnail.png"))
                refresh(screen, s)
                s.current_index = s.current_index + 1

    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
    pygame.quit()
    loop.close()

if __name__ == "__main__":
    cfg = init_config()
    init_pygame(cfg)
    asyncio.run(main(cfg))
