import asyncio
import importlib
from datetime import datetime

import aiohttp.web
import click

import bottery
from bottery.conf import settings
from bottery.log import Spinner


class Bottery:
    _loop = None
    _session = None
    _server = None

    # This is a feature trial, do NOT rely your application on it
    active_conversations = {}

    def __init__(self):
        self.tasks = []

    @property
    def session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(loop=self.loop)
        return self._session

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    @property
    def server(self):
        if self._server is None:
            self._server = aiohttp.web.Application()
        return self._server

    def import_msghandlers(self):
        mod = importlib.import_module(settings.ROOT_MSGCONF)
        return mod.msghandlers

    async def configure_platforms(self):
        platforms = settings.PLATFORMS.items()
        if not platforms:
            raise Exception('No platforms configured')

        global_options = {
            'active_conversations': self.active_conversations,
            'registered_handlers': self.import_msghandlers(),
            'server': self.server,
            'loop': self.loop,
            'session': self.session,
        }

        for engine_name, platform in platforms:
            if not platform.get('OPTIONS'):
                platform['OPTIONS'] = {}
            platform['OPTIONS'].update(global_options)
            platform['OPTIONS']['engine_name'] = engine_name

            mod = importlib.import_module(platform['ENGINE'])

            with Spinner('Configuring %s' % engine_name.title()):
                engine = mod.engine(**platform['OPTIONS'])
                await engine.configure()
                self.tasks.extend(engine.tasks)

        for task in self.tasks:
            self.loop.create_task(task())

    def configure_server(self, port):
        handler = self.server.make_handler()
        setup_server = self.loop.create_server(handler, '0.0.0.0', port)
        self.loop.run_until_complete(setup_server)
        click.echo('Server running at http://localhost:{port}'.format(
            port=port,
        ))

    def exception_handler(self, loop, context):
        click.echo(context.get('exception'))
        loop.default_exception_handler(context)
        # We don't use Bottery.stop() here because the current implementation
        # won't stop the running loop.
        loop.stop()

    def configure(self):
        self.loop.run_until_complete(self.configure_platforms())
        self.loop.set_exception_handler(self.exception_handler)

    def run(self, server_port):
        click.echo('{now}\n{bottery} version {version}'.format(
            now=datetime.now().strftime('%B %d, %Y -  %H:%M:%S'),
            bottery=click.style('Bottery', fg='green'),
            version=bottery.__version__
        ))

        self.configure()

        if self._server is not None:
            self.configure_server(port=server_port)

        # if not self.tasks:
        #     click.secho('No tasks found.', fg='red')
        #     self.stop()
        #     sys.exit(1)

        click.echo('Quit the bot with CONTROL-C')
        self.loop.run_forever()

    def stop(self):
        self.session.close()
        self.loop.close()
