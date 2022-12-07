import os
import random
import socket
import tempfile
import threading
import time
from subprocess import Popen, PIPE

from jet_bridge_base.logger import logger


class SSHTunnel(object):
    local_bind_port = None
    process = None
    check_thread = None
    tunnel_timeout = 10.0

    def __init__(self, name, conf, on_close=None):
        self.conf = conf
        self.name = name
        self.on_close = on_close

    def is_tunnel_alive(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.tunnel_timeout)

        try:
            connect_to = ('127.0.0.1', self.local_bind_port)
            s.connect(connect_to)
            s.sendall('Hello, world'.encode('utf-8'))
            s.recv(1024)

            return True
        except socket.error:
            return False
        finally:
            s.close()

    def run_ssh_tunnel_process(self):
        private_key_str = self.conf.get('ssh_private_key').replace('\\n', '\n')

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(private_key_str.encode('utf-8'))
            keyfile = f.name

        listen = 'localhost:{}:{}:{}'.format(self.local_bind_port, self.conf.get('host'), self.conf.get('port'))
        command = ['ssh', '-N', '-L', listen, '-i', keyfile]

        if self.conf.get('ssh_port'):
            command.extend(['-p', str(self.conf.get('ssh_port'))])

        command.extend(['{}@{}'.format(self.conf.get('ssh_user'), self.conf.get('ssh_host'))])

        process = Popen(
            command,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE
        )

        process.stdout.readlines()
        os.unlink(keyfile)

        return_code = process.poll()

        if return_code is not None:
            error = '\n'.join(map(lambda x: x.decode('utf-8'), process.stderr.readlines()))
            raise Exception(error)

        return process

    def execute_check_thread(self, process):
        while True:
            return_code = process.poll()

            if return_code is not None:
                logger.info('SSH tunnel is terminated (CODE: {})'.format(return_code))
                break
            elif not self.is_tunnel_alive():
                logger.info('SSH tunnel is dropped')
                process.kill()
                break

            time.sleep(5)

        if self.on_close:
            self.on_close()

    def start(self):
        self.local_bind_port = random.randint(10000, 65535)
        self.process = self.run_ssh_tunnel_process()

        self.check_thread = threading.Thread(
            target=self.execute_check_thread,
            args=(self.process,),
            name='Tunnel-check-{}'.format(self.name)
        )
        self.check_thread.start()

    def close(self):
        if self.process:
            self.process.kill()
