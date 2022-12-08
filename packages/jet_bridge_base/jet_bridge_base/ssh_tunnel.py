import os
import random
import socket
import tempfile
import threading
import time
from subprocess import Popen, PIPE

from jet_bridge_base.logger import logger


class SSHTunnel(object):
    local_bind_host = '127.0.0.1'
    local_bind_port = None
    process = None
    check_thread = None
    tunnel_timeout = 10.0

    def __init__(
        self,
        name,
        ssh_host,
        ssh_port,
        ssh_user,
        ssh_private_key,
        remote_host,
        remote_port,
        on_close=None
    ):
        self.name = name
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_private_key = ssh_private_key
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.on_close = on_close

    def is_tunnel_alive(self):
        connect_to = (self.local_bind_host, self.local_bind_port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.tunnel_timeout)

        try:
            s.connect(connect_to)
            s.sendall('Hello, world'.encode('utf-8'))
            s.recv(1024)

            return True
        except socket.error:
            return False
        finally:
            s.close()

    def run_ssh_tunnel_process(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(self.ssh_private_key.encode('utf-8'))
            keyfile = f.name

        listen = 'localhost:{}:{}:{}'.format(self.local_bind_port, self.remote_host, self.remote_port)
        command = ['ssh', '-N', '-L', listen, '-i', keyfile, '-o', 'StrictHostKeyChecking=no']

        if self.ssh_port:
            command.extend(['-p', str(self.ssh_port)])

        command.extend(['{}@{}'.format(self.ssh_user, self.ssh_host)])

        try:
            process = Popen(
                command,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE
            )
        except FileNotFoundError:
            raise Exception('SSH is not installed')

        process.stdout.readlines()
        os.unlink(keyfile)

        return_code = process.poll()

        if return_code is not None:
            error = '\n'.join(map(lambda x: x.decode('utf-8'), process.stderr.readlines()))
            raise Exception(error)

        return process

    def execute_check_thread(self, process):
        while True:
            time.sleep(5)
            return_code = process.poll()

            if return_code is not None:
                logger.info('SSH tunnel is terminated (CODE: {})'.format(return_code))
                break
            elif not self.is_tunnel_alive():
                logger.info('SSH tunnel is dropped')
                process.kill()
                break

        if self.on_close:
            self.on_close()

    @property
    def is_active(self):
        return self.is_tunnel_alive()

    def is_port_used(self, port):
        connect_to = (self.local_bind_host, port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            if s.connect_ex(connect_to) == 0:
                return True
            else:
                return False
        finally:
            s.close()

    def get_unused_port(self):
        while True:
            port = random.randint(10000, 65535)
            if not self.is_port_used(port):
                return port

    def start(self):
        self.local_bind_port = self.get_unused_port()
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
