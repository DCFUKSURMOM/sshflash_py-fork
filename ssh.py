import paramiko

DEBUG_MODE = False

def connect(host):
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
      client.connect(host, username="root", password="${EMPTY}", look_for_keys=False, timeout=1)
      return client
    except TimeoutError:
        if DEBUG_MODE:
            print(f"Unable to reach host at {host}")
        return None

def do_command_single(host, cmd, stdin=None):
    client = connect(host)
    _stdin, _stdout, _stderr = client.exec_command(cmd)
    if stdin:
        _stdin.write(stdin)
        _stdin.channel.shutdown_write()
    out = _stdout.read()
    client.close()
    return out


def do_command_batch(host, cmds):
    client = connect(host)
    outputs = []
    try:
        for c in cmds:
            _stdin, _stdout, _stderr = client.exec_command(c)
            outputs.append(_stdout.read())
    except Exception as e:
        print(f"Exception running SSH commands! {e}")
        return None
    client.close()
    return outputs

def do_command_and_write_output(host, cmd, output_filename):
    out = do_command_single(host, cmd)
    open(output_filename, 'xb').write(out)

def do_command_with_stdin_file(host, cmd, input_filename):
    return do_command_single(host, cmd, open(input_filename, 'rb').read())
