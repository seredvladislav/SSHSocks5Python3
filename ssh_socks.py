# -*- mode: python ; coding: utf-8 -*-
import asyncio, asyncssh, sys
import pdb
import time
import logging
import aiohttp
from aiohttp_socks import SocksConnector, SocksVer
from concurrent.futures._base import TimeoutError
import traceback
import json
import contextlib

LOCK = asyncio.Lock()
logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger('[ssh_socks]')


# asyncssh.set_debug_level(3)


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.read()


async def get_external_ip(socks_host, socks_port):
    connector = SocksConnector. \
        from_url('socks5://{socks_host}:{socks_port}'.format(socks_host=socks_host, socks_port=socks_port))

    async with aiohttp.ClientSession(connector=connector) as session:
        _need_close = False
        try:
            result = await fetch(session, 'https://lumtest.com/myip.json')
        except (aiohttp.client_exceptions.ClientConnectorError):
            _need_close = True
            logger.error('Connection failed: ClientConnectorError')
        except Exception as exc:
            _need_close = True
            logger.error('Connection failed: %s' % exc)
            # traceback.print_exc()
        if _need_close:
            logger.error("Can't get external ip address.")
            return
        if not result:
            return
        try:
            data = json.loads(result)
        except json.decoder.JSONDecodeError:
            logger.error("Can't decode json, failed get external ip address.")
            return
        async with LOCK:
            logger.info('####################')
            logger.info(data)
            logger.info('####################')
        return data


async def run_socks(ssh_host, ssh_user, ssh_password, socks_host, socks_port, _timeout=10, keepalive_interval=10):
    try:
        conn, client = await asyncio.wait_for(
            asyncssh.create_connection(
                client_factory=None, host=ssh_host, username=ssh_user,
                password=ssh_password, known_hosts=None, agent_path=None,
                keepalive_interval=keepalive_interval,
            )
            , _timeout)
    except TimeoutError:
        logger.error("Failed start socks5 server, TimeoutError.")
        return
    listener = await conn.forward_socks(socks_host, socks_port)
    logger.info("listen on port: {port} for {host}".format(port=listener.get_port(), host=socks_host))
    await asyncio.sleep(1)
    data = await get_external_ip(socks_host=socks_host, socks_port=socks_port)
    if not data:
        conn.close()
        logger.error("Failed start socks5 server.")
        return
    await conn.wait_closed()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-ssh', help='ssh', dest='ssh_host', required=True)
    parser.add_argument('-p', '-P', dest='ssh_port', help='port', type=int, default=22)
    parser.add_argument('-l', dest='ssh_user', help='login', required=True)
    parser.add_argument('-pw', dest='ssh_password', help='password')
    parser.add_argument('-D', dest='socks', help='dynamic SOCKS', default='127.0.0.1:7000')
    args, unknown = parser.parse_known_args(sys.argv[1:])

    socks_host, socks_port = args.socks.split(':')
    socks_host = socks_host.strip()
    socks_port = int(socks_port)
    try:
        asyncio.get_event_loop(). \
            run_until_complete(run_socks(args.ssh_host, args.ssh_user, args.ssh_password, socks_host, socks_port))
    except (KeyboardInterrupt, SystemExit):
        pass
    except (OSError, asyncssh.Error) as exc:
        sys.exit('SSH connection failed: %s' % exc)


if __name__ == '__main__':
    main()
