import asyncio
import configparser
import ipaddress
import logging
import os
import random
import socket
from io import StringIO
from pathlib import Path

from kademlia.utils import digest

import src.avails.constants as const
from src.avails import connect
from src.configurations import logger as _logger
from src.core.app import AppType


def print_app(app):
    ip_version = ipaddress.ip_address(app.this_ip.ip).version
    print_string = (
        f'\n:configuration choices{"=" * 32}\n'
        f'{"USERNAME": <15} : {app.this_remote_peer.username: <10}\n'
        f'{"THIS_IP": <15} : {f"{app.this_ip}": <10}\n'
        f'{"PROTOCOL": <15} : {f"{const.PROTOCOL}": <10}\n'
        f'{"IP_VERSION": <15} : {ip_version: <10}\n'
        f'{"SERVER_IP": <15} : {f"{const.SERVER_IP}": <10}\n'
        f'{"MULTICAST_IP": <15} : {f"{const.MULTICAST_IP_v4 if ip_version == 4 else const.MULTICAST_IP_v6}": <10}\n'
        f'{"PORT_THIS": <15} : {const.PORT_THIS: <10}\n'
        f'{"SERVER_PORT": <15} : {const.PORT_SERVER: <10}\n'
        f'{"NETWORK_PORT": <15} : {const.PORT_NETWORK: <10}\n'
        f'{"PAGE_PORT": <15} : {const.PORT_PAGE: <10}\n'
        f'{"PORT_REQ": <15} : {const.PORT_REQ: <10}\n'
        f'{"=" * 56}\n'
    )
    with const.LOCK_PRINT:
        print('GLOBAL VERSION', const.VERSIONS['GLOBAL'])
        return print(print_string)


def _get_local_appdata():
    if const.IS_WINDOWS:
        return Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"), const.APP_NAME)
    else:
        return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"), const.APP_NAME)


def set_paths():
    """
    Current Setup
    * log config is present at applevel
    * basic config is present at local user data directories
    * all logs are written into local user data directories
    * webpage at applevel
    """
    path_app_data = _get_local_appdata()
    path_app_data.mkdir(exist_ok=True)
    config_path = Path(path_app_data, 'configs')
    config_path.mkdir(exist_ok=True)

    const.PATH_LOG = Path(path_app_data, 'logs')

    const.PATH_CURRENT = Path(os.getcwd())
    const.PATH_LOG.mkdir(exist_ok=True)
    const.PATH_PAGE = Path(const.PATH_CURRENT, 'webpage')
    const.PATH_LOG_CONFIG = Path(const.PATH_CURRENT, 'configs', const.LOG_CONFIG_NAME)

    const.PATH_CONFIG_FILE = Path(config_path, const.DEFAULT_CONFIG_FILE_NAME)
    const.PATH_PROFILES = Path(config_path, 'profiles')
    const.PATH_PROFILES.mkdir(exist_ok=True)
    const.PATH_CONFIG = config_path

    downloads_path = Path(Path.home(), 'Downloads')
    # check if the directory exists
    if not downloads_path.exists():
        downloads_path = Path(Path.home(), 'Desktop')

    const.PATH_DOWNLOAD = Path(os.path.join(downloads_path, const.APP_NAME))

    try:
        os.makedirs(const.PATH_DOWNLOAD, exist_ok=True)
    except OSError as e:
        _logger.error(f"Error creating directory: {e} from set_paths()")
        const.PATH_DOWNLOAD = Path(path_app_data, 'downloads')
        const.PATH_DOWNLOAD.mkdir(exist_ok=True)

    print_paths()


async def load_configs(app: AppType):
    config_map = configparser.ConfigParser(allow_no_value=True)

    def _helper():
        try:
            config_map.read(const.PATH_CONFIG_FILE)
            # access required keys
            _ = config_map['USER_PROFILES']
            _ = config_map['NERD_OPTIONS']
            _ = config_map['VERSIONS']
            _ = config_map['SELECTED_PROFILE']
        except KeyError:
            _write_default_configurations(const.PATH_CONFIG_FILE)
            config_map.read(const.PATH_CONFIG_FILE)

        if not any(tuple(Path(const.PATH_PROFILES).glob("*.ini"))):
            _write_default_profile(Path(const.PATH_PROFILES, const.DEFAULT_PROFILE_NAME), config_map)

        with open(const.PATH_CONFIG_FILE, 'w+') as fp:
            config_map.write(fp)  # noqa

    async def finalize_config():

        def _finalize_config_helper():
            if _logger.level == logging.DEBUG:
                config_buffer = StringIO()
                config_map.write(config_buffer)
                _logger.debug(f"writing configurations:")
                _logger.debug(config_buffer.getvalue())
            else:
                _logger.info("writing final configurations")

            with open(const.PATH_CONFIG_FILE, 'w+') as fp:
                config_map.write(fp)  # noqa
                # write the final state of configuration when exiting application

        return await asyncio.to_thread(_finalize_config_helper)

    await asyncio.to_thread(_helper)
    set_constants(config_map)
    app.current_config = config_map
    app.exit_stack.push_async_callback(finalize_config)


def _write_default_configurations(path):
    default_config_file = (
        "[NERD_OPTIONS]\n"
        f"ip_version = {4 if const.IP_VERSION == socket.AF_INET else 6}\n"
        "protocol = tcp\n"
        f"this_port = {const.PORT_THIS}\n"
        f"req_port = {const.PORT_REQ}\n"
        f"page_port = {const.PORT_PAGE}\n"
        f"page_serve_port = {const.PORT_PAGE_SERVE}\n"
        "\n"
        "[VERSIONS]\n"
        "global = 1.1\n"
        "rp = 1.1\n"
        "fo = 1.1\n"
        "do = 1.1\n"
        "wire = 1.1\n"
        "\n"
        "[USER_PROFILES]\n"
        f"{const.DEFAULT_PROFILE_NAME}\n"
        "\n"
        "[SELECTED_PROFILE]\n"
        f"{const.DEFAULT_PROFILE_NAME}\n"
    )
    with open(path, 'w+') as config_file:
        config_file.write(default_config_file)


def _write_default_profile(profile_path, config_map):
    default_profile_file = (
        "[USER]\n"
        "name = new user\n"
        f"id = {int.from_bytes(digest(random.randbytes(160)))}\n"
        "\n"
        "[INTERFACE]\n"
        "\n"
        "[TRANSFERS AGREED]\n"
    )
    with open(profile_path, 'w+') as profile_file:
        profile_file.write(default_profile_file)

    config_map.set('USER_PROFILES', profile_path.name)


def set_constants(config_map: configparser.ConfigParser) -> bool:
    """Sets global constants from values in the configuration file and directories.

    Reads configuration values from default_config.ini and sets global variables accordingly.
    Also sets directory paths for logs and the webpage.

    Returns:
        bool: True if configuration values were flip successfully, False otherwise.
    """

    const.PORT_THIS = config_map.getint('NERD_OPTIONS', 'this_port')
    const.PORT_REQ = config_map.getint('NERD_OPTIONS', 'req_port')
    const.PORT_PAGE = config_map.getint('NERD_OPTIONS', 'page_port')
    const.PAGE_SERVE_PORT = config_map.getint('NERD_OPTIONS', 'page_serve_port')

    const.PROTOCOL = connect.TCPProtocol if config_map['NERD_OPTIONS']['protocol'] == 'tcp' else connect.UDPProtocol
    const.IP_VERSION = socket.AF_INET6 if config_map['NERD_OPTIONS']['ip_version'] == '6' else socket.AF_INET

    const.VERSIONS = {k.upper(): float(v) for k, v in config_map['VERSIONS'].items()}

    if const.IP_VERSION == socket.AF_INET6 and not socket.has_ipv6:
        _logger.warning(f"system does not support ipv6 ({socket.has_ipv6=}), using ipv4")
        const.IP_VERSION = socket.AF_INET

    if const.IP_VERSION == socket.AF_INET6:
        const.USING_IP_V6 = True
        const.USING_IP_V4 = False
        const.BIND_IP = const._BIND_IP_V6

    return True


def print_paths():
    print(*(f"{x}={getattr(const, x)}" for x in dir(const) if x.startswith("PATH")), sep="\n")
