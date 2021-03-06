import sys
import unittest

from _pydevd_bundle import pydevd_comm

import ptvsd.pydevd_hooks
from ptvsd.socket import Address
from ptvsd._local import run_module, run_file, run_main
from tests.helpers.argshelper import _get_args


class FakePyDevd(object):

    def __init__(self, __file__, handle_main):
        self.__file__ = __file__
        self.handle_main = handle_main

    @property
    def __name__(self):
        return object.__repr__(self)

    def main(self):
        self.handle_main()


class RunBase(object):

    def setUp(self):
        super(RunBase, self).setUp()
        self.argv = None
        self.addr = None
        self.kwargs = None

    def _run(self, argv, addr, **kwargs):
        self.argv = argv
        self.addr = addr
        self.kwargs = kwargs

    def _no_debug_runner(self, addr, filename, is_module, *extras, **kwargs):
        self.addr = addr
        self.argv = sys.argv
        self.filename = filename
        self.is_module = is_module
        self.args = extras
        self.kwargs = kwargs


class RunModuleTests(RunBase, unittest.TestCase):

    def test_local(self):
        addr = (None, 8888)
        run_module(addr, 'spam', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args('--module', '--file', 'spam:'))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})

    def test_server(self):
        addr = Address.as_server('10.0.1.1', 8888)
        run_module(addr, 'spam', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args('--module', '--file', 'spam:'))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})

    def test_remote(self):
        addr = ('1.2.3.4', 8888)
        run_module(addr, 'spam', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args('--module', '--file', 'spam:',
                                   ptvsd_extras=['--client', '1.2.3.4']))

        self.assertEqual(self.addr, Address.as_client(*addr))
        self.assertEqual(self.kwargs, {
            'singlesession': True,
        })

    def test_remote_localhost(self):
        addr = Address.as_client(None, 8888)
        run_module(addr, 'spam', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args(
                             '--module', '--file', 'spam:',
                             ptvsd_extras=['--client', 'localhost']))

        self.assertEqual(self.addr, Address.as_client(*addr))
        self.assertEqual(self.kwargs, {
            'singlesession': True,
        })

    def test_extra(self):
        addr = (None, 8888)
        run_module(addr, 'spam', '--vm_type', 'xyz', '--', '--DEBUG',
                   _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args(
                             '--module', '--file', 'spam:', '--DEBUG',
                             ptvsd_extras=['--vm_type', 'xyz']))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})

    def test_executable(self):
        addr = (None, 8888)
        run_module(addr, 'spam', _run=self._run)

        self.assertEqual(self.argv,
                         _get_args(
                             '--module', '--file', 'spam:',
                             prog=sys.argv[0]))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})


class RunScriptTests(RunBase, unittest.TestCase):

    def test_local(self):
        addr = (None, 8888)
        run_file(addr, 'spam.py', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args('--file', 'spam.py'))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})

    def test_server(self):
        addr = Address.as_server('10.0.1.1', 8888)
        run_file(addr, 'spam.py', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args('--file', 'spam.py'))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})

    def test_remote(self):
        addr = ('1.2.3.4', 8888)
        run_file(addr, 'spam.py', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args(
                             '--file', 'spam.py',
                             ptvsd_extras=['--client', '1.2.3.4']))

        self.assertEqual(self.addr, Address.as_client(*addr))
        self.assertEqual(self.kwargs, {
            'singlesession': True,
        })

    def test_remote_localhost(self):
        addr = Address.as_client(None, 8888)
        run_file(addr, 'spam.py', _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args(
                             '--file', 'spam.py',
                             ptvsd_extras=['--client', 'localhost']))

        self.assertEqual(self.addr, Address.as_client(*addr))
        self.assertEqual(self.kwargs, {
            'singlesession': True,
        })

    def test_extra(self):
        addr = (None, 8888)
        run_file(addr, 'spam.py', '--vm_type', 'xyz', '--', '--DEBUG',
                 _run=self._run, _prog='eggs')

        self.assertEqual(self.argv,
                         _get_args(
                             '--file', 'spam.py', '--DEBUG',
                             ptvsd_extras=['--vm_type', 'xyz']))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})

    def test_executable(self):
        addr = (None, 8888)
        run_file(addr, 'spam.py', _run=self._run)

        self.assertEqual(self.argv,
                         _get_args('--file', 'spam.py', prog=sys.argv[0]))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})


class IntegratedRunTests(unittest.TestCase):

    def setUp(self):
        super(IntegratedRunTests, self).setUp()
        self.___main__ = sys.modules['__main__']
        self._argv = sys.argv
        self._start_server = pydevd_comm.start_server
        self._start_client = pydevd_comm.start_client

        self.pydevd = None
        self.addr = None
        self.kwargs = None
        self.maincalls = 0
        self.mainexc = None
        self.exitcode = -1

    def tearDown(self):
        sys.argv[:] = self._argv
        sys.modules['__main__'] = self.___main__
        sys.modules.pop('__main___orig', None)
        pydevd_comm.start_server = self._start_server
        pydevd_comm.start_client = self._start_client
        # We shouldn't need to restore __main__.start_*.
        super(IntegratedRunTests, self).tearDown()

    def _install(self, pydevd, addr, **kwargs):
        self.pydevd = pydevd
        self.addr = addr
        self.kwargs = kwargs
        return self

    def _main(self):
        self.maincalls += 1
        if self.mainexc is not None:
            raise self.mainexc

    def test_run(self):
        pydevd = FakePyDevd('pydevd/pydevd.py', self._main)
        addr = (None, 8888)
        run_file(addr, 'spam.py', _pydevd=pydevd, _install=self._install)

        self.assertEqual(self.pydevd, pydevd)
        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})
        self.assertEqual(self.maincalls, 1)
        self.assertEqual(sys.argv,
                         _get_args('--file', 'spam.py', prog=sys.argv[0]))
        self.assertEqual(self.exitcode, -1)

    def test_failure(self):
        self.mainexc = RuntimeError('boom!')
        pydevd = FakePyDevd('pydevd/pydevd.py', self._main)
        addr = (None, 8888)
        with self.assertRaises(RuntimeError) as cm:
            run_file(addr, 'spam.py', _pydevd=pydevd, _install=self._install)
        exc = cm.exception

        self.assertEqual(self.pydevd, pydevd)
        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})
        self.assertEqual(self.maincalls, 1)
        self.assertEqual(sys.argv,
                         _get_args('--file', 'spam.py', prog=sys.argv[0]))
        self.assertEqual(self.exitcode, -1)  # TODO: Is this right?
        self.assertIs(exc, self.mainexc)

    def test_exit(self):
        self.mainexc = SystemExit(1)
        pydevd = FakePyDevd('pydevd/pydevd.py', self._main)
        addr = (None, 8888)
        with self.assertRaises(SystemExit):
            run_file(addr, 'spam.py', _pydevd=pydevd, _install=self._install)

        self.assertEqual(self.pydevd, pydevd)
        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertEqual(self.kwargs, {})
        self.assertEqual(self.maincalls, 1)
        self.assertEqual(sys.argv,
                         _get_args('--file', 'spam.py', prog=sys.argv[0]))
        self.assertEqual(self.exitcode, 1)

    def test_installed(self):
        pydevd = FakePyDevd('pydevd/pydevd.py', self._main)
        addr = (None, 8888)
        run_file(addr, 'spam.py', _pydevd=pydevd)

        __main__ = sys.modules['__main__']
        expected_server = ptvsd.pydevd_hooks.start_server
        expected_client = ptvsd.pydevd_hooks.start_client
        for mod in (pydevd_comm, pydevd, __main__):
            start_server = getattr(mod, 'start_server')
            if hasattr(start_server, 'orig'):
                start_server = start_server.orig
            start_client = getattr(mod, 'start_client')
            if hasattr(start_client, 'orig'):
                start_client = start_client.orig

            self.assertIs(start_server, expected_server,
                          '(module {})'.format(mod.__name__))
            self.assertIs(start_client, expected_client,
                          '(module {})'.format(mod.__name__))


class NoDebugRunTests(RunBase, unittest.TestCase):
    def test_nodebug_script_args(self):
        addr = (None, 8888)
        args = ('--one', '--two', '--three')
        run_main(addr, 'spam.py', 'script', *args,
                 _runner=self._no_debug_runner)

        self.assertEqual(self.argv, ['spam.py'] + list(args))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertFalse(self.is_module)
        self.assertEqual(self.args, args)
        self.assertEqual(self.kwargs, {})

    def test_nodebug_script_no_args(self):
        addr = Address.as_server('10.0.1.1', 8888)
        run_main(addr, 'spam.py', 'script',
                 _runner=self._no_debug_runner)

        self.assertEqual(self.argv, ['spam.py'])

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertFalse(self.is_module)
        self.assertEqual(self.args, ())
        self.assertEqual(self.kwargs, {})

    def test_nodebug_module_args(self):
        addr = (None, 8888)
        args = ('--one', '--two', '--three')
        run_main(addr, 'spam.py', 'module', *args,
                 _runner=self._no_debug_runner)

        self.assertEqual(self.argv, ['spam.py'] + list(args))

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertTrue(self.is_module)
        self.assertEqual(self.args, args)
        self.assertEqual(self.kwargs, {})

    def test_nodebug_module_no_args(self):
        addr = Address.as_server('10.0.1.1', 8888)
        run_main(addr, 'spam.py', 'module',
                 _runner=self._no_debug_runner)

        self.assertEqual(self.argv, ['spam.py'])

        self.assertEqual(self.addr, Address.as_server(*addr))
        self.assertTrue(self.is_module)
        self.assertEqual(self.args, ())
        self.assertEqual(self.kwargs, {})
