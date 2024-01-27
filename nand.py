import os
import ssh
import tarfile
import time
 
def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def dump_nand_device(d, host, qualifier):
      if qualifier:
        qualifier = f"{d.name}_{int(time.time())}_{qualifier}"
      else:
        qualifier = qualifier = f"{d.name}_{int(time.time())}"
      dirpath = os.path.join("dumps", qualifier)

      os.mkdir(dirpath)
      mtds_raw = ssh.do_command_single(host, "find /dev -name 'mtd[0-9]'")
      mtds = sorted(mtds_raw.decode().split("\n")[:-1])
      for partition in mtds:
        cmd = f"mtdinfo {partition} | grep -E 'Name|Type' | cut -b 33-"
        mtdinfo = ssh.do_command_single(host, cmd)
        partname, type, _ =  mtdinfo.decode().split('\n')
        partname = partname.replace('_', '-')
        if partname.lower() in ['rfs', 'bulk']:
          print(f"Dumping ubifs (tar) {partition} ({type}) {partname}")
          cmds_mount = [f"ubiattach -p {partition}", f"mount -t ubifs /dev/ubi0_0 /mnt/root "]
          ssh.do_command_batch(host, cmds_mount)

          cmd = f"tar -c -f - -C /mnt/root ."
          tarpath = os.path.join(dirpath, f"{partition[5:]}_{type}-ubifs_{partname}.tar")
          ssh.do_command_and_write_output(host, cmd, tarpath)

          cmds_unmount = [f"umount /mnt/root ", f"ubidetach -d 0 "]
          ssh.do_command_batch(host, cmds_unmount)
        else:
          print(f"Dumping raw {partition} ({type}) {partname}")
          cmd = f"nanddump --bb=skipbad -a --skip-bad-blocks-to-start {partition}"
          imgpath = os.path.join(dirpath, f"{partition[5:]}_{type}_{partname}.img")
          ssh.do_command_and_write_output(host, cmd, imgpath)
      make_tarfile(f'dumps/{qualifier}.tar.gz', dirpath)

def restore_nand_device(d, host, args):
  archive_path = os.path.join("dumps/", args)
  restore_path = "restore_tmp"

  try:
    os.mkdir(restore_path)
  except OSError as error:
    print(error)

  file = tarfile.open(archive_path)  
  file.extractall(restore_path)
  file.close()

  img_root_path = os.path.join(restore_path, args[:-7])
  images = os.listdir(img_root_path)

  for i in images:
    mtd, part_type, name = i[:-4].split('_')
    img_path = os.path.join(img_root_path, i)
    if part_type == 'nor':
      print(f"{mtd} {name}: NOR flash restoration not supported yet.")
    elif part_type == 'nand-ubifs':
      print(f"{mtd} {name}: Restoring UBIFS volume...", end='', flush=True)
      write_nand_ubifs_partition(d, host, mtd, img_path, name)
      print(f"Done!")
    elif part_type == 'nand':
      print(f"{mtd} {name}: Restoring Raw NAND Partition...", end='', flush=True)
      write_nand_raw_partition(d, host, mtd, img_path)
      print(f"Done!")
    else:
      print(f"{mtd} {name}: Unrecognized partition type {part_type}")
  return True

def write_nand_ubifs_partition(d, host, partition, partfile, volname):
  if volname == 'Bulk':
    print('Changing name to ubi_bulk')
    volname = 'ubi_bulk'
  cmds_setupubi = [f'/usr/sbin/ubiformat -y /dev/{partition}', 
                    f'/usr/sbin/ubiattach -p /dev/{partition}',
                    f'/usr/sbin/ubimkvol /dev/ubi0 -N {volname} -m',
                    f'mount -t ubifs /dev/ubi0_0 /mnt/tmp']
  ssh.do_command_batch(host, cmds_setupubi)

  writecmd = "tar x -f '-' -C /mnt/tmp"
  ssh.do_command_with_stdin_file(host, writecmd, partfile)

  cmds_teardownubi = [f'umount /mnt/tmp', 
                    f'/usr/sbin/ubidetach -d 0',
                    f'sync']
  ssh.do_command_batch(host, cmds_teardownubi)


def write_nand_raw_partition(d, host, partition, partfile):
  ssh.do_command_single(host, f"/usr/sbin/flash_erase /dev/{partition} 0 0")
  writecmd = f"/usr/sbin/nandwrite -p /dev/{partition} -"
  ssh.do_command_with_stdin_file(host, writecmd, partfile)