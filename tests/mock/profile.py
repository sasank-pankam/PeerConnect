import getpass
import random

from src.core.app import provide_app_ctx
from src.managers import ProfileManager, profilemanager


@provide_app_ctx
async def profile_getter(ip, *, app_ctx=None):
    p = await ProfileManager.add_profile(
        getpass.getuser(),
        {
            "USER": {
                "name": getpass.getuser() + str(ip),
                "id": random.getrandbits(255),
            },
            "SERVER": {
                "port": 45000,
                "ip": "0.0.0.0",
                "id": 0,
            },
            "INTERFACE": {
                "ip": ip,
                "scope_id": -1,
                "if_name": b'{TEST}',
                "friendly_name": "testing",
            } if ip else {}
        }
    )

    async def delete(*_):
        await ProfileManager.delete_profile(p.file_name)

    app_ctx.exit_stack.push_async_exit(delete)
    return p


async def mock_profile(config):
    if config.test_mode == 'host':
        ip = f"127.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(2, 255)}"
    else:
        ip = None
    await profilemanager.set_current_profile(await profile_getter(ip))
