import argparse
import asyncio
import re
import urllib.parse
import sys


def control_output(s):
    print("\t|\t")
    for line in s.split("\n"):
        print(f"\t|\t{line}")


async def print_http_headers(url):
    url = urllib.parse.urlsplit(url)
    if url.scheme == 'https':
        reader, writer = await asyncio.open_connection(
            url.hostname, 443, ssl=True)
    else:
        reader, writer = await asyncio.open_connection(
            url.hostname, 80)

    query = (
        f"HEAD {url.path or '/'} HTTP/1.0\r\n"
        f"Host: {url.hostname}\r\n"
        f"\r\n"
    )

    writer.write(query.encode('latin-1'))
    while True:
        line = await reader.readline()
        if not line:
            break

        line = line.decode('latin1').rstrip()
        if line:
            print(f'HTTP header> {line}')

    # Ignore the body, close the socket
    writer.close()


async def start_server(args) -> None:
    async def tunnel(local_reader, local_writer):
        remote_reader, remote_writer = await asyncio.open_connection(args.host, args.port)
        local_addr = local_writer.get_extra_info('peername')
        remote_addr = remote_writer.get_extra_info('peername')
        print(f"Connection opened from {local_addr!r} to {remote_addr!r}")
        while True:
            print(f"local_reader: {local_reader.at_eof()}")
            send = await local_reader.read(64 * 1024)
            if not send:
                break
            print(f"Received {send[0:60]!r} from {local_addr!r}")


            remote_writer.write(send)
            print("x1")
            await remote_writer.drain()
            print("x2")

            while True:
                print("read remote")
                receive = await remote_reader.read(64 * 1024)
                print(f"Received {receive[0:60]!r} from {remote_addr!r}")
                if not receive:
                    break
                # print(f'remote read: {receive.docode()!r}')
                print("x4")
                local_writer.write(receive)
                print("x5")
                await local_writer.drain()

            #if local_reader.at_eof():
            #    if remote_writer.can_write_eof():
            #        print("Writing eof")
            #        remote_writer.write_eof()
            
            print("x6")
            
        remote_writer.close()
        local_writer.close()
        # if not remote_writer.is_closing():
        #     print("Closing remote")
        #     remote_writer.write_eof()
        # if not local_writer.is_closing():
        #     print("local close")
        #     local_writer.write_eof()
        
    server = await asyncio.start_server(tunnel, args.laddr, args.lport)

    # addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    # print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple transparent HTTP proxy (web tunnel)")
    parser.add_argument("-a", "--local-interface", dest="laddr", help="Local interface to bind to", default="localhost")
    parser.add_argument("-p", "--local-port", dest="lport", help="Local port to open", type=int, default=8880)
    # parser.add_argument("-r", "--replace-hostname", dest="replace_hostname", help="Replace hostname in http requests")
    # parser.add_argument("-d", "--downgrade-http", dest="downgrade_http",  action="count", help="Downgrade responses to HTTP/1.0")
    parser.add_argument("-v", "--verbose", default=0, action="count", help="Increase output verbosity")
    parser.add_argument("host", help="Host address of remote machine to forward to")
    parser.add_argument("port", help="Port of remote machine to forward to", type=int)

    args = parser.parse_args()

    asyncio.run(start_server(args))
    
    return 0


if __name__ == "__main__":
    exit(main())
