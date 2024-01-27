import pager
import cbf
import sys
from interface import config as conn_iface
from mount import connection as mount_connection

def do_surgeon_boot(path, mem):
    """
Usage:
surgeon_boot <path to surgeon.cbf>

Uploads a Surgeon.cbf file to a device in USB Boot mode. 
File can be any name, but must conform to CBF standards.
    """
    wrapped_cbf = cbf.create(ipath=path, opath='/dev/null', mem=mem, write_file=False)
    pager_client = pager.client(conn_iface(mount_connection()))
    pager_client.upload_bytes(wrapped_cbf)
    print('Booting surgeon.')  