import argparse
import datetime
import logging
import logging.handlers
import os
import os.path
import sys
from pathlib import Path

# TODO: Add version info when package setup is complete
BUDGY_VERSION = "2.0.0-dev"

class BudgyApp(object):
    def __init__(self, app_name):
        self._app_name = app_name
        self._parser:argparse.ArgumentParser = self._create_parser()
        self._add_base_command_args()
        self._add_command_args()
        self._args = self.parse_command_line()
        self._setup_logging()


    @property
    def arg_parser(self):
        return self._parser

    def _create_parser(self):
        return argparse.ArgumentParser(self._app_name)

    def _add_base_command_args(self):
        """
        Add standard logging command line arguments
        """
        self._parser.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='INFO',
            help='Set the logging level (default: INFO)'
        )
        self._parser.add_argument(
            '--log-dir',
            type=Path,
            default=Path.home() / '.config' / 'budgy' / 'logs',
            help='Set the log directory (default: ~/.config/budgy/logs/)'
        )
        self._parser.add_argument(
            '--log-console',
            action='store_true',
            help='Log to both file and console'
        )

    def _add_command_args(self):
        """
        Override this command to add args to self._parser
        :return: None
        """
        pass

    def parse_command_line(self):
        return self._parser.parse_args()

    def _setup_logging(self):
        """
        Configure logging based on command line arguments.
        Sets up file logging with rotation and optional console logging.
        """
        # Ensure log directory exists
        log_dir = self._args.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging level
        log_level = getattr(logging, self._args.log_level.upper())
        
        # Set up formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set up file logging with rotation (3 files, 3KB each)
        app_name_safe = os.path.basename(self._app_name).lower().replace(" ", "-")
        log_file = log_dir / f'{app_name_safe}.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=3 * 1024,  # 3KB
            backupCount=2,      # Keep 2 backup files (total of 3 files)
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Set up console logging if requested
        if self._args.log_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Log the configuration
        logging.info(f'Logging configured: level={self._args.log_level}, file={log_file}, console={self._args.log_console}')

    def _create_app_header(self):
        header = ''
        header += '##############################\n'
        header += '#\n'
        header += f'# {os.path.basename((sys.argv[0]))}\n'
        header += f'# budgy {BUDGY_VERSION}\n'
        header += f'# Start Time: {datetime.datetime.now()}\n'
        header += '#\n'
        header += '##############################\n'

        return header

    def print_app_header(self):
        header = self._create_app_header()
        print(header)

    def log_app_header(self):
        header = self._create_app_header()
        for line in header.splitlines():
            logging.info(line)

    def run(self):
        pass