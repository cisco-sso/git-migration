import os
import sys
import click
import logging
from app import utils

# FORMAT = '%(asctime)s %(levelname)s:%(filename)s:%(lineno)d %(message)s'
# logging.basicConfig(format=FORMAT, level=logging.INFO)
log = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(auto_envvar_prefix='COMPLEX', help_option_names=['-h', '--help'])


class Context(object):
    def __init__(self):
        self.verbose = False
        self.home = os.getcwd()

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        # click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)


pass_context = click.make_pass_decorator(Context, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands'))


class AppCLI(click.MultiCommand):
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')
            mod = __import__('app.commands.cmd_' + name, None, None, ['cli'])
        except ImportError as e:
            log.error("Failed to find command {} error=[{}]".format(name, e))
            sys.exit(1)
            return
        return mod.cli


@click.command(cls=AppCLI, context_settings=CONTEXT_SETTINGS)
# @click.option('--home',
#               type=click.Path(exists=True, file_okay=False, resolve_path=True),
#               help='Changes the folder to operate on.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.option('--console-log-level',
              type=click.Choice(['debug', 'info', 'warning', 'error', 'critical'], case_sensitive=False),
              default=utils.LogUtils.get_console_log_level(),
              help="Filter logs to show on STDOUT")
@click.option('--console-log-normal',
              is_flag=True,
              default=utils.LogUtils.get_console_log_normal(),
              help="Print normal logs to STDOUT instead of JSON")
@click.option('--file-log-level',
              type=click.Choice(['debug', 'info', 'warning', 'error', 'critical'], case_sensitive=False),
              default=utils.LogUtils.get_file_log_level(),
              help="Filter logs to print to file")
@pass_context
def app(ctx, verbose, console_log_level, console_log_normal, file_log_level):
    """The Git-Migration CLI"""
    ctx.verbose = verbose
    ctx.console_log_level = console_log_level
    ctx.console_log_normal = console_log_normal
    ctx.file_log_level = file_log_level
    print("Console log normal", console_log_normal)
    ctx.log = utils.LogUtils.get_logger(os.path.basename(__file__), console_log_level, console_log_normal,
                                        file_log_level)
    # if home is not None:
    #     ctx.home = home
