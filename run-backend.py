#!/usr/bin/env python3

import os
import shutil
import math
import time
import argparse
import json

import asyncio
from aiomqtt import Client, MqttError

import numpy as np

temp_dir="temp"
#temp_dir="/dev/shm/rxviz-temp"


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
        self.tps = float("nan")
        self.best_llh = float("nan")
        self.llh = float("nan")
        self.tree = ""

    def set_input_data(self, new_data):
        changed = False
#        new_data = settings.get_input_data()
        if new_data["example"] != self.example:
            self.example = new_data["example"]
            changed = True
        if new_data["tree_mode"] != self.tree_mode:
            self.tree_mode = new_data["tree_mode"]
            changed = True
        if new_data["num_trees"] != self.num_trees:
            self.num_trees = int(new_data["num_trees"])
            changed = True
        return changed

    def restart(self):
        self.done = False

        self.current_index = 0
        self.best_index = -1
        self.tps = float("nan")
        self.best_llh = float("nan")
        self.llh = float("nan")

    def update_llh(self, llh):
        self.llh = llh
        if self.best_llh != self.best_llh or llh > self.best_llh:
            self.best_llh = llh
            self.best_index = self.current_index


def to_string(num):
    if num != num:
        return ""
    else:
        return str(round(num, 1))

######################### DATA SETTINGS #######################################

all_examples = [("Animals", "animal"), ("Languages", "language"), ("Horses", "horse")]
models = {"language" : "BIN+G", "animal" : "GTR+G400", "horse" : "GTR+G"}



def init_dir():
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

############################## MAIN LOOP ##################################

s = Status()

class MQTTClient(object):
  recv_queue: asyncio.Queue
  send_queue: asyncio.Queue
  
  def __init__(self, config):
    self.hostname = config.get("mqtt_host", "localhost")
    self.port = config.get("mqtt_port", 1883)
    self.username = config.get("mqtt_user", None)
    self.password = config.get("mqtt_password", None)
    self.sub_topic = config.get("cmd_topic", "raxviz/command")
    self.pub_topic = config.get("upd_topic", "raxviz/status")
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
      print(data)
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

class RaxmlRunner:

  def __init__(self, config, mqtt):
#    self.hostname = config.get("host", "localhost")
    self.mqtt = mqtt
    
  async def async_run(self, cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

  async def run_eval(self):
    #generate tree
    command = "./raxml-ng --start"
    command += " --tree " + s.tree_mode + "{1}"
    command += " --model " + models[s.example]
    command += " --msa " + os.path.join("msa", s.example + ".phy")
    command += " --prefix " + os.path.join(temp_dir, "generate")
    command += " --seed " + str(s.current_index)
    command += " --threads auto --redo"
    t0 = time.time()
    await self.async_run(command)
    t1 = time.time()

    #evaluate tree
    command = "./raxml-ng --evaluate "
    command += " --msa " + os.path.join("msa", s.example + ".phy")
    command += " --tree " + os.path.join(temp_dir, "generate.raxml.startTree")
    command += " --model " + models[s.example]
    command += " --prefix " + os.path.join(temp_dir, "evaluate")
    command += " --seed 2 --threads auto --lh-epsilon 0.001 --extra compat-v11 --redo"
    await self.async_run(command)

  async def parse_output(self):
    with open(os.path.join(temp_dir, "evaluate.raxml.bestTree"), "r") as treefile:
      s.tree = treefile.read().rstrip()

    llh = float("nan")
    rt = float("nan")
    with open(os.path.join(temp_dir, "evaluate.raxml.log"), "r") as logfile:
      for line in logfile:
        if line.startswith("Final LogLikelihood: "):
            llh = float(line.split(": ")[1])
        if line.startswith('Elapsed time:'):
            rt = float(line.split()[2])
        if not math.isnan(rt) and not math.isnan(llh):
           break

    s.update_llh(llh)
    s.tps = 1.0 / rt
    s.current_index = s.current_index + 1
    if s.current_index == s.num_trees:
      s.done = True

  async def send_mqtt(self):
    data = {}
    data["llh"] = s.llh
    data["tps"] = s.tps
    data["tree"] = s.tree
    self.mqtt.put_msg(data)

  async def process_commands(self):
    data = self.mqtt.get_msg()
#    print(data)
    if data:
      print(data["cmd"])
      if data["cmd"] == "start":
        s.paused = False
      elif data["cmd"] == "pause":
        s.paused = True
      elif data["cmd"] == "restart":
        s.restart()
      elif data["cmd"] == "settings":
        s.set_input_data(data)

  async def spin(self):
    while s.running:
      await self.process_commands()
      if not s.paused and not s.done:
        await self.run_eval()
        await self.parse_output()
        await self.send_mqtt()
      else:
        await asyncio.sleep(0.05)

############################## MAIN ##################################

def init_config():
    parser = argparse.ArgumentParser(description="VizRax backend")
    parser.add_argument("--broker", type=str, default="localhost", help="Address of the MQTT server")
    args = parser.parse_args()
    
    cfg = {}
    cfg["mqtt_host"] = args.broker
    return cfg

async def main():
    cfg = init_config()
    
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)    

    mqtt = MQTTClient(cfg)
    rax = RaxmlRunner(cfg, mqtt)
    
    settings = { "example": "animal", "tree_mode": "rand", "num_trees": 100}
    s.set_input_data(settings)
    
    spins = [mqtt.spin(), rax.spin()]
    tasks = [asyncio.create_task(t) for t in spins]
    for t in tasks:
      await t    

    if os.path.isdir(temp_dir):
      shutil.rmtree(temp_dir)
  
if __name__ == '__main__':    
    asyncio.run(main())    
