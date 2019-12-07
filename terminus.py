import socketserver
import socket
from multiprocessing import Pool, Queue
from time import sleep
from os import remove
from sys import exit
from pathlib import Path
import signal

MQ = MESSAGE_QUEUE = Queue()

def initializer():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

class Logger:
    '''Basic logger class. The TCP and UDP servers will extend
    this class and inherit the `Logger.log` method.
    '''

    def __init__(self):
        'Ensure that the "template" variable is defined for the class.'

        assert 'template' in self.__class__,(
            f'{self.__class__.name} must have a "template"' + \
            ' variable for logging. Exiting!'
        )

    def get_proto(self):
        'Get the protocol by class name'

        return self.__class__.__name__

    def get_client_address(self):
        'Get the IP address of the server'

        return self.client_address[0]

    def get_message(self):
        'Build and return the log message'
        
        return self.__class__.template.format(self.get_proto(),
                self.get_client_address())
    
    def log(self):
        'Craft a log message and write it to a socket.'

        MQ.put(self.get_message())

class TCP(socketserver.BaseRequestHandler,Logger):
    'Basic TCP handler'

    template = '{} connection received from: {}'

    def handle(self):
        self.log()
        self.request.sendall(b'Connection successful!')
        self.request.close()

class UDP(socketserver.BaseRequestHandler,Logger):
    'Basic UDP handler'

    template = '{} data received from: {}'

    def handle(self):
        self.log()
        pass

class SCTP(Logger):
    'Basic SCTP handler'

    template = '{} connection received from: {}'

    @staticmethod
    def log(addr):

        MQ.put(SCTP.template.format('SCTP',addr))

def start_tcp(host,port):
    'Start a TCP server'

    with socketserver.TCPServer((host,port), TCP) as server:
        server.timeout=1
        server.serve_forever()

def start_udp(host,port):
    'Start a UDP server'

    with socketserver.UDPServer((host,port), UDP) as server:
        server.timeout=1
        server.serve_forever()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser('Description here')
    parser.add_argument('--interface-address','-ip',
        required=True,
        help='''IP address of the network interface that the TCP and
        UDP servers will bind to during operation.''')
    parser.add_argument('--tcp-port','-tp',
        required=True, type=int,
        help='Port number for the TCP server to listen on.')
    parser.add_argument('--udp-port','-up',
        required=True, type=int,
        help='Port number for the UDP server to listen on.')
    args = parser.parse_args()
    
    pool = Pool(2,initializer=initializer)

    print('Starting the servers...')

    pool.apply_async(start_tcp,(args.interface_address,args.tcp_port,))
    pool.apply_async(start_udp,(args.interface_address,args.udp_port,))

    print('Starting echo server...')

    try:

        while True: print(MQ.get())

    except KeyboardInterrupt as e:
        print('\n^C captured. Shutting down...')
    finally:
        pool.terminate()
        pool.join()

    print('Done')
