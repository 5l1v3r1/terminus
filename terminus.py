import socketserver
import socket
import signal
from multiprocessing import Pool, Queue
from time import sleep
from os import remove
from sys import exit
from pathlib import Path
from OpenSSL import crypto, SSL

def initializer():
    'Ignore keyboard interrupts in child processes'
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
def generate_certificate(certfile, keyfile):
    'Generate a random SSL certificate'

    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 1024)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C  = "US"
    cert.get_subject().ST = str(randint(1,10000000))
    cert.get_subject().L  = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    cert.get_subject().O  = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
    cert.get_subject().OU = "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD" 
    cert.get_subject().CN = "EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    open(certfile, "wb").write(
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    open(keyfile, "wb").write(
        crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

class Logger:
    '''Basic logger class. The TCP and UDP servers will extend
    this class and inherit the `Logger.log` method.
    '''
    
    # Queue for simple transfer of alerts between
    # processes
    MQ = MESSAGE_QUEUE = Queue()

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

        Logger.MQ.put(self.get_message())

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

        while True: print(Logger.MQ.get())

    except KeyboardInterrupt as e:
        print('\n^C captured. Shutting down...')
    finally:
        pool.terminate()
        pool.join()

    print('Done')
