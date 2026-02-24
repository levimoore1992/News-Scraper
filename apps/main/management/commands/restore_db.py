import logging
import os
import subprocess
from typing import Dict, List
import sys

import dj_database_url

from django.conf import settings
from django.core.management import BaseCommand


def create_command(db_config: Dict[str, str], command_template: str, *args) -> str:
    """
    Create a command based on the command template and given arguments.

    Args:
        db_config (Dict[str, str]): Database configuration.
        command_template (str): Command template.
        *args: Additional arguments for the command template.

    Returns:
        str: Formatted command.
    """
    return command_template.format(
        db_config["host"], db_config["username"], db_config["dbname"], *args
    )


ERROR_CANNOT_DUMP_PROD = "Cannot dump into production."
ERROR_DB_NOT_VALID = "{} is not a valid {}. Available options: {}"
ERROR_SAME_DB = "Source and target databases are the same. Exiting."
ERROR_BACKUP_FILE_MISSING = "The backup file '{}' does not exist. Exiting."
WARNING_ON_LIVE_SERVER = "Running the `restore_local_db` command on a live server."
NO_COMMANDS_MESSAGE = "No commands to be run. Exiting."
CONFIRM_RUN_COMMANDS = "\nThe following commands will be run:"


class Command(BaseCommand):
    """Command to restore db on local development"""

    help = """This command is purely for local development because on a clean database these options wont exist"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("management")

        # Parse database URLs
        local_db_config = dj_database_url.parse(os.environ.get("DATABASE_URL", ""))
        production_db_config = dj_database_url.parse(
            os.environ.get("PRODUCTION_DATABASE_URL", "")
        )

        # Set up database configurations
        self.database_config = {
            "local": {
                "host": local_db_config.get("HOST"),
                "dbname": local_db_config.get("NAME"),
                "username": local_db_config.get("USER"),
                "password": local_db_config.get("PASSWORD"),
                "port": local_db_config.get("PORT", "5432"),
            },
            "production": {
                "host": production_db_config.get("HOST"),
                "dbname": production_db_config.get("NAME"),
                "username": production_db_config.get("USER"),
                "password": production_db_config.get("PASSWORD"),
                "port": production_db_config.get("PORT", "5432"),
            },
        }

    def add_arguments(self, parser):
        """
        Add command line arguments to the parser.
        """
        parser.add_argument(
            "-s",
            "--source",
            type=str,
            help="Indicates what database you want to get the dump file from, "
            "options are local, test, develop, production. If no "
            "source is given, it will first try to use an existing dump.",
            default=None,
        )

        parser.add_argument(
            "-t",
            "--target",
            type=str,
            help="Indicates what database you want to load the dump file to, "
            "options are local, test, develop",
            default="local",
        )

        parser.add_argument(
            "-f",
            "--file-name",
            type=str,
            help="Name of the dumpfile",
            default="restore.dump",
        )
        parser.add_argument(
            "-nd",
            "--no-drop",
            help="Flag if you dont want to drop the db",
            dest="drop",
            action="store_false",
        )
        parser.add_argument(
            "-nr",
            "--no-restore",
            help="Flag if you dont want to restore the db",
            dest="restore",
            action="store_false",
        )

        parser.add_argument(
            "--no-input",
            help="Skip user prompts. Does not skip entering passwords for non local databases.",
            action="store_true",
        )

    def validate_arguments(self, source: str, target: str, file_name: str) -> None:
        """
        Validate the provided command arguments and exit if they are not valid.
        """
        available_dbs = self.database_config.keys()

        if target == "production":
            self.stdout.write(ERROR_CANNOT_DUMP_PROD)
            sys.exit(1)

        if target not in available_dbs:
            self.stdout.write(
                ERROR_DB_NOT_VALID.format(target, "target", ", ".join(available_dbs))
            )
            sys.exit(1)

        if source:
            if source not in available_dbs:
                self.stdout.write(
                    ERROR_DB_NOT_VALID.format(
                        source, "source", ", ".join(available_dbs)
                    )
                )
                sys.exit(1)
            if source == target:
                self.stdout.write(ERROR_SAME_DB)
                sys.exit(0)
        else:
            if not os.path.exists(file_name):
                self.stdout.write(ERROR_BACKUP_FILE_MISSING.format(file_name))
                sys.exit(1)

    def run_commands(self, commands: List[str], env: Dict) -> None:
        """
        Execute the given commands.
        """
        for command in commands:
            try:
                subprocess.check_call(command, env=env, shell=True)
            except subprocess.CalledProcessError as e:
                self.stdout.write(f"Command failed with error: {e}")

    def handle(self, *args, **kwargs):
        """
        Handle the management command.
        """
        if not settings.DEBUG:
            self.logger.error(WARNING_ON_LIVE_SERVER)
            sys.exit(1)

        source = kwargs["source"]
        target = kwargs["target"]
        file_name = kwargs["file_name"]

        # Don't use temporary files - just use the specified file_name directly

        self.validate_arguments(source, target, file_name)

        # Only generate source commands if a source is explicitly provided
        # If no source is provided and restore.dump exists, we'll use that file directly
        source_commands = []
        if source:
            source_commands = self.generate_source_commands(source, file_name)

        target_commands = self.generate_target_commands(target, kwargs, file_name)

        all_commands = source_commands + target_commands
        if not all_commands:
            self.stdout.write(NO_COMMANDS_MESSAGE)
            sys.exit(0)

        self.stdout.write(CONFIRM_RUN_COMMANDS)
        for command in all_commands:
            self.stdout.write(f"\t- {command}")

        if (
            not kwargs["no_input"]
            and input("Would you like to continue? Type 'y' or 'n' ").lower() != "y"
        ):
            self.stdout.write("Exiting now")
            sys.exit(0)

        # Only run source commands if a source is provided
        if source:
            self.run_commands(source_commands, self.get_env_for_db(source))
        self.run_commands(target_commands, self.get_env_for_db(target))

    def generate_source_commands(self, source: str, file_name: str) -> List[str]:
        """
        Generate the source commands based on the provided source and file_name.
        """
        source_commands = []
        if source:
            db_config = self.database_config[source]
            command = (
                f"pg_dump -Fc -v --host={db_config['host']} --port={db_config['port']} "
                f"--username={db_config['username']} --dbname={db_config['dbname']} -f {file_name}"
            )
            source_commands.append(command)
        return source_commands

    def generate_target_commands(
        self, target: str, kwargs: Dict, file_name: str
    ) -> List[str]:
        """
        Generate the target commands based on the provided target and kwargs.
        """
        target_commands = []
        db_config = self.database_config[target]

        if kwargs["drop"] and kwargs["restore"]:
            drop_table_path = os.path.join(
                settings.BASE_DIR,
                "apps/main/management/commands/sql/drop_tables.sql",
            )
            command = (
                f"psql --host={db_config['host']} --port={db_config['port']} "
                f"--username={db_config['username']} --dbname={db_config['dbname']} -f {drop_table_path}"
            )
            target_commands.append(command)

        if kwargs["restore"]:
            setup_path = os.path.join(
                settings.BASE_DIR, "apps/courses/management/commands/sql/setup.sql"
            )
            command = (
                f"psql --host={db_config['host']} --port={db_config['port']} "
                f"--username={db_config['username']} --dbname={db_config['dbname']} -f {setup_path}"
            )
            target_commands.append(command)

            # Always use the specified file_name (restore.dump by default)
            command = (
                f"pg_restore -v --no-owner --host={db_config['host']} --port={db_config['port']} "
                f"--username={db_config['username']} --dbname={db_config['dbname']} {file_name}"
            )
            target_commands.append(command)

        return target_commands

    def get_env_for_db(self, db_name: str) -> Dict:
        """
        Get the environment for the provided database name.
        """
        env = os.environ.copy()
        env["PGPASSWORD"] = self.database_config[db_name]["password"]
        return env
