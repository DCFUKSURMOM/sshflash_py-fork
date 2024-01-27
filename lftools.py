from cmd import Cmd

import device
import mmc
import nand
import os
import paramiko
import pdb
import sys
import ssh
import surgeon
import time
import usb.core
# find USB devices

import tarfile
import os.path

def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


paramiko.util.log_to_file("test.log", level = "DEBUG")

def find_device(host):
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
      client.connect(host, username="root", password="${EMPTY}", look_for_keys=False, timeout=1)
    except TimeoutError:
        print(f"Unable to reach host at {host}")
        return False
    _stdin, _stdout, _stderr = client.exec_command("df")
    #print(_stdout.read())
    client.close()
    print(f"Found a retroleap host at {host}")
    return True


def find_alive_device():
    if find_device("169.254.6.1"):
        return "Booted"
    elif find_device("169.254.8.1"):
        return "Surgeon"
    else:
        return None


def wait_for_device():
  while(True):
    for d in device.devices:
      dev = usb.core.find(idVendor=d.surgeon_vid, idProduct = d.surgeon_pid)
      if dev:
        print(f"Found leapfrog device {d.name} in surgeon mode")
        return d.name
    time.sleep(1)
    foo = find_alive_device()
    if foo:
        print(foo)
        return foo


def get_device_surgeon_only():
    device_obj = device.get_device_to_surgeon()
    if not device_obj:
      print("No device found or device not in bootloader or surgeon mode.")
      return None
    return device_obj

class LFTools(Cmd):
  def do_get_to_surgeon(self, args):
    """Detect whether a device is present"""
    print(device.get_device_to_surgeon())
    return
    
  def do_dump_device(self, args):
    device = get_device_surgeon_only()
    if not device:
      return
    if device.flash_type == 'MMC':
      mmc.dump_mmc_device(device, "169.254.8.1", args)
    elif device.flash_type == 'NAND':
      nand.dump_nand_device(device, "169.254.8.1", args)
    else:
      print("Unknown device flash type {device.flash_type}")

  def do_dump_device_mmc(self, args):
      device = get_device_surgeon_only()
      if not device:
        return
      mmc.dump_mmc_device(device, "169.254.8.1", args)
      #return True

    
  def do_restore_device(self, args):
    dev = get_device_surgeon_only()
    if not dev:
      return
    if dev.flash_type == 'MMC':
      mmc.restore_mmc_device(dev, "169.254.8.1", args)
    elif dev.flash_type == 'NAND':
      nand.restore_nand_device(dev, "169.254.8.1", args)
    else:
      print("Unknown device flash type {device.flash_type}")

  def do_restore_device_mmc(self, args):
    device = get_device_surgeon_only()
    if not device:
      return
    mmc.restore_mmc_device(device,"169.254.8.1", args)
    #return True

  def do_identify_device(self, args):
    type, dev = device.identify_device()
    print(f"type = {type} dev = {dev}")

  def do_boot_surgeon(self, args):
    surgeon.do_surgeon_boot(args)

  def do_restore_nand_device(self, args):
    dev = get_device_surgeon_only()
    if not dev:
      return
    host = '169.254.8.1'
    if len(args) < 1:
      print("Syntax: restore_nand_device <archive filename>")
      return
    nand.restore_nand_device(dev, host, args)


if __name__ == '__main__':
  prompt = LFTools()
  prompt.prompt = '> '
  prompt.cmdloop('Welcome to LFTools, ya dig?')