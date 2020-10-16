"""A module for parsing configuration file for processeses handler."""

import sys

import yaml

class ConfigParser():
    """A class which handle parsing file."""
    
    OPTIONS_INT = [
            'numprocs',
            'autostart',
            'startsecs',
            'startretries',
            'stopwaitsecs',
            'umask',
            ]

    OPTIONS_AR = [
            'unexpected',
            True,
            False,
            ]

    OPTIONS_SS = [
            'TERM',
            'QUIT',
            'KILL',
            'HUP',
            'INT',
            'USR1',
            'USR2',
            ]

    OPTIONS_STD = [
            'AUTO',
            None,
            ]


    def __init__(self, taskmaster):
        """Initialize attributes related to configuration file"""
        self.programs = {}
        self.umask = None
        self.filename = taskmaster.filename


    def parse(self):
        """Parse the content of the file."""
        self.programs.clear()
        self._fetch_file_content()
        return 0


    def _fetch_file_content(self):
        """Load all the data in the file into an object"""
        try:
            with open(self.filename) as f:
                self.stream = yaml.safe_load(f)
                print("----------")
                print(self.stream)
                print("----------")
        except FileNotFoundError:
            print("TaskMasterd: No such file or directory: " + self.filename)
            raise SystemExit(1)
        except yaml.YAMLError:
            print("YAML: Error: bad file format.")
            raise SystemExit(1)
        else:
            ret = self._check_integrity_content()
            if ret:
                print("Bad file architecture !")
                raise SystemExit(1)
        return 0


    def _check_integrity_content(self):
        """Verify all the architecture of the stream object."""
        if type(self.stream) is dict:
            # print(self.stream.items())
            for program, content in self.stream.items():
                if type(program) is str:
                    if type(content) is list:
                        for elem in content:
                            if type(elem) is not dict:
                                return -6
                        if self._check_options(program, content):
                            return -1
                        if program != "taskmaster":
                            if self._make_config_program(program, content):
                                return -2
                    else:
                        return -3
                else:
                    return -4
        else:
            return -5


    def _taskmaster_options_handler(self, program_name, options):
        """Check the options of taskmaster and handle them."""
        for elem in options:
            for k, v in elem.items():
                if k == 'umask':
                    if self.umask:
                        print("umask already set.")
                        sys.exit(-1)
                    if type(v) != type(int()) or v < 0 or v > 0o777:
                        print(f"'{k}' incorrect value.")
                        sys.exit(-1)
                    self.umask = v
        return 0


    def _options_limit(self, key, value):
        """Check if the options values are not out of bound."""
        if key == 'umask' and value < 0:
            print(f"{key} must be greater or equal to 0.")
            return -1
        if key == 'numprocs' and value <= 0:
            print(f"'{key}' must be greater or equal to 1.")
            return -1
        elif key == 'autostart' and (value != True and value != False):
            print(f"'{key}' needs True of False.")
            return -1
        elif (key == 'startsecs' or key == 'startretries' or key == 'stopwaitsecs') and value < 0:
            print(f"'{key}' must be greater or equal than 0.")
            return -1
        return 0


    def _check_options(self, program_name, options):
        """Verify if the 'command' option exists and if options are unique."""
        keys = []
        if program_name in self.programs.keys():
            print("ERROR: several same programs.")
            sys.exit(-1)
        if program_name == 'taskmaster':
            return self._taskmaster_options_handler(program_name, options)
        for elem in options:
            for k, v in elem.items():
                keys.append(k)
            if 'command' in elem.keys():
                if not elem['command']:
                    print("ERROR: command option need a 'path'")
                    return -1
        if 'command' not in keys:
            print("ERROR: No 'command' option specified.")
            return -1
        while len(keys):
            key = keys.pop()
            if key in keys:
                print(f"ERROR: {key}: appears several times")
                return -1
        return 0


    def _outputs_handler(self, prog_name):
        """Check if stdout_logfile and stderr_logfile have the same output."""
        if self.programs[prog_name]['stdout_logfile'] == self.programs[prog_name]['stderr_logfile'] \
        and self.programs[prog_name]['stdout_logfile'] not in self.OPTIONS_STD:
            print("stdout_logfile and stderr_logfile have the same name.")
            return -1
        return 0

    def _make_config_program(self, program_name, options):
        """Fetch data from one program and add it to the list of programs."""
        self.programs[program_name] = {
                'command': None,
                'numprocs': 1,
                'autostart': True,
                'autorestart': 'unexpected',
                'exitcodes': 0,
                'startsecs': 1,
                'startretries': 3,
                'stopsignal': 'TERM',
                'stopwaitsecs': 0,
                'stdout_logfile': None,
                'stderr_logfile': None,
                'env': {},
                'directory': None,
                'running': None,
                'gave_up': None,
                'umask': None,
#                'timestamp': 0,
                }
        for option in options:
            for k, v in option.items():
                if k in self.programs[program_name].keys():
                    if self._check_value_option(program_name, k, v):
                        return -1
        if self._outputs_handler(program_name):
            return -1
        return 0


    def _check_value_option(self, program_name, key, value):
        """Check if the option's value has the appropriate type.""" 
        if key in self.OPTIONS_INT:
            if key == 'exitcodes':
                if type(value) is not list or type(value) is not int:
                    return -1
                if type(value) is list:
                    for i in value:
                        if type(i) is not int:
                            return -1
            elif type(value) == bool or type(value) == int:
                if self._options_limit(key, value):
                    return -1
            else:
                return -1
                #print(f"{key}: '{value}' Not an integer.")
        elif key == 'autorestart':
            if value not in self.OPTIONS_AR:
                print(f"autorestart: '{value}' unknown: 'unexpected', 'true' or 'false' expected.")
                return -1
        elif key == 'stopsignal':
            if value not in self.OPTIONS_SS:
                print(f"stopsignal: '{value}' unknown: 'TERM' or 'QUIT' expected")
                return -1
        elif key == 'stdout_logfile' or key == 'stderr_logfile':
            if (key == 'stdout_logfile' or key == 'stderr_logfile') and value == 'None':
                value = None
            elif type(value) != str:
                print(f"{key}: '{value}' unknown: 'AUTO', 'None' or a path expected")
                return -1
        if key == 'env':
            if type(value) is not type(str()):
                print("env: a string expected `KEY=value`.")
                return -1
            Dict = dict((k.strip(), v.strip()) for k, v in (env.split('=') for env in value.split(',')))
            print(Dict)
            value = Dict
        self.programs[program_name][key] = value
        return 0

    def _spread_content(self):
        """Cut the file content and get one process information."""
#       ...
        return 0
