import os
import ssh
import tarfile
import time
import pdb
 
def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def dump_mmc_device(d, host, qualifier):
      #pdb.set_trace()
      if qualifier:
        qualifier = f"{d.name}_{int(time.time())}_{qualifier}"
      else:
        qualifier = qualifier = f"{d.name}_{int(time.time())}"
      dirpath = os.path.join("dumps", qualifier)
      os.mkdir(dirpath)

      # mbr special case
      imgpath = os.path.join(dirpath, f"mbr.img")
      ssh.do_command_and_write_output(host, "dd if=/dev/mmcblk1 bs=512 count=1", imgpath)

      # Now do the partitions
      parts_raw = ssh.do_command_single(host, "find /dev -name 'mmcblk0p[0-9]'")
      parts = sorted(parts_raw.decode().split("\n")[:-1])
      for partition in parts:
        if partition.lower() in ['/dev/mmcblk0p3', '/dev/mmcblk0p4']:
          print(f"Dumping mmc (tar) {partition}")
          cmds_mount = [f"mount -t ext4 {partition} /mnt/root "]
          ssh.do_command_batch(host, cmds_mount)
          cmd = f"tar -c -f - -C /mnt/root ."
          tarpath = os.path.join(dirpath, f"{partition[5:]}-ext4.tar")
          ssh.do_command_and_write_output(host, cmd, tarpath)
          cmds_unmount = [f"umount /mnt/root "]
          ssh.do_command_batch(host, cmds_unmount)
        else:
          print(f"Dumping raw mmc: {partition}")
          cmd = f"dd if={partition} bs=16384"
          imgpath = os.path.join(dirpath, f"{partition[5:]}.img")
          ssh.do_command_and_write_output(host, cmd, imgpath)
      make_tarfile(f'dumps/{qualifier}.tar.gz', dirpath)


def restore_mmc_device(d, host, archive_path):
  restore_path = "restore_tmp"

  try:
    os.mkdir(restore_path)
  except OSError as error:
    print(error)

  file = tarfile.open(os.path.join('dumps/', archive_path))  
  file.extractall(restore_path)
  file.close()

  img_path = os.path.join(restore_path, archive_path[:-7])
  images = os.listdir(img_path)

  for i in images:
    partition = i[:-4].split('-')[0]

    if partition == 'mbr':
      ssh.do_command_with_stdin_file(host, "dd of=/dev/mmcblk0 count=1 bs=512", os.path.join(img_path, i))
      print(f"Restoring MBR")
      
    elif i[-4:] == '.tar':
      print(f"Restoring ext4 partition {partition}")
      cmds_setupext4 = [f'mkfs.ext4 -F /dev/{partition} -O ^metadata_csum', 
                        f'mount -t ext4 /dev/{partition} /mnt/root']
      ssh.do_command_batch(host, cmds_setupext4)

      ssh.do_command_with_stdin_file(host, f"tar x -f '-' -C /mnt/root", os.path.join(img_path, i))

      ssh.do_command_single(host, "umount /mnt/root")

    elif i[-4:] == '.img':
      print(f"restoring raw image {partition}")
      ssh.do_command_with_stdin_file(host, f"dd of=/dev/{partition} bs=16384", os.path.join(img_path, i))

    else:
      print(f"{mtd} {name}: Unrecognized partition type {part_type}")
  return True