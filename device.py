import paramiko
import usb.core
from time import sleep
import pdb
import surgeon
from collections import namedtuple

Device = namedtuple("Device", "name friendlyname surgeon_vid surgeon_pid flash_type family board_ids")

devices = [
# lf1000_kernel/arch/arm/mach-lf1000/board_ids.h
# FIXME: Didj emeraldboot ID currently the same as LX!
Device("didj", "Didj w/ EmeraldBoot", 0x0f63, 0xDEAD, "NAND", "lf1000_didj", [0x03, 0x04]),
Device("lx", "Leapster Explorer", 0x0f63, 0x0016, "NAND", "lf1000", [0x01, 0x02, 0x06, 0x07, 0x0A]),
Device("leappad1", "LeapPad 1", 0x0f63, 0x001b, "MMC", "lf1000_leappad", [0x0B, 0x0C, 0x0D]),
# lf2000_kernel/arch/arm/mach-nxp3200/include/mach/board_revisions.h
Device("leapstergs", "Leapster GS (Lucy)", 0x0f63, 0x001d, "NAND", "lf2000", [0x205, 209, 300]),
Device("leappad2", "LeapPad 2 (Valencia)", 0x0f63, 0x001f, "NAND", "lf2000", list(range(0x206, 0x218)) + [0x310]),
Device("leappadultra", "LeapPad Ultra/XDi (Rio)", 0x0f63, 0x0025, "NAND", "lf2000", list(range(0x320, 0x32E))),
# lf3000_kernel/arch/arm/mach-nxp4330/include/mach/board_revisions.h
Device("leappadplatinum", "LeapPad Platinum (Bogota)", 0x0f63, 0x002c, "MMC", "lf3000", list(range(0x501, 0x507)))
        ]

surgeon_memloc = {
  "lf1000_didj": "high",
  "lf1000_leappad": "high",
  "lf1000": "high",
  "lf2000": "superhigh",
  "lf3000": "superhigh"
  }

def identify_booted_device(host):
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
      client.connect(host, username="root", password="${EMPTY}", look_for_keys=False, timeout=1)
    except TimeoutError:
      print(f"Unable to reach host at {host}")
      return False

    board = -1
    cmd = "cat /sys/devices/platform/lf1000-gpio/board_id"
    _stdin, _stdout, _stderr = client.exec_command(cmd)
    lf1k = _stdout.read()
    if lf1k: 
      board = int(lf1k.decode(), 16)
    else:
      cmd = "cat /sys/devices/system/board/system_rev"
      _stdin, _stdout, _stderr = client.exec_command(cmd)
      board = int(_stdout.read().decode(), 16)
    client.close()
    for d in devices:
        if board in d.board_ids:
                return d
    return None

def identify_bootloader_device():
  for d in devices:
    dev = usb.core.find(idVendor=d.surgeon_vid, idProduct = d.surgeon_pid)
    if dev:
      print(f"Found leapfrog device {d.name} in surgeon mode")
      return d
  return None

def identify_device():
  surgeon_dev = identify_booted_device("169.254.8.1")
  if surgeon_dev:
    print(f"Found {surgeon_dev.name} in surgeon mode")
    return 'SURGEON', surgeon_dev
  retroleap_dev = identify_booted_device("169.254.6.1")
  if retroleap_dev:
    print(f"Found {retroleap_dev.name} in retroleap mode. Please reboot the device in surgeon mode.")
    return 'RETROLEAP', retroleap_dev
  bootloader_dev = identify_bootloader_device()
  if bootloader_dev:
    print(f"Found {bootloader_dev.name} in bootloader mode.")
    return 'BOOTLOADER', bootloader_dev
  print("No device found! Did you turn it on?")
  return 'NO_DEVICE', None

def get_surgeon_path(device):
  return f'retroleap/{device.family}_surgeon_zImage'

def get_device_to_surgeon():
  type, device = identify_device()
  if type == 'BOOTLOADER':
    surgeon.do_surgeon_boot(get_surgeon_path(device), surgeon_memloc[device.family])
    print("Surgeon sent. Waiting for surgeon to come up")
    sleep(5)
    while not identify_booted_device("169.254.8.1"):
      sleep(2)
      print("Still waiting for surgeon...")
    return identify_booted_device("169.254.8.1")
  elif type == 'SURGEON':
    return device
  elif type == 'RETROLEAP':
    print("Surgeon reboot on retroleap not supported yet.")
  elif type == 'NO_DEVICE':
    print("No device found!")
  else:
    print(f"Invalid type {type}")
  return None

