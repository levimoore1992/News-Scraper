import subprocess
from io import StringIO
from unittest import mock

from django.test import TestCase, override_settings
from django.core.management import call_command
from apps.main.management.commands.restore_db import (
    Command,
    NO_COMMANDS_MESSAGE,
    create_command,
)


@override_settings(DEBUG=True)
@mock.patch.dict(
    "os.environ",
    {
        "DATABASE_URL": "postgres://test_user:test_pass@localhost:5432/test_db",
        "PRODUCTION_DATABASE_URL": "postgres://prod_user:prod_pass@prod_host:5432/prod_db",
    },
)
class RestoreDbCommandTest(TestCase):
    """
    Test suite for the restore_db command.
    """

    def setUp(self):
        """
        Set up the test suite.
        :return: None
        """
        self.command = Command()

    def test_create_command_formats_correctly(self) -> None:
        """
        Ensure create_command formats the command template using db_config
        and additional arguments in the correct order.
        """
        db_config: dict[str, str] = {
            "host": "localhost",
            "username": "test_user",
            "dbname": "test_db",
        }

        template: str = "psql -h {} -U {} -d {} -f {}"
        result: str = create_command(db_config, template, "schema.sql")

        expected: str = "psql -h localhost -U test_user -d test_db -f schema.sql"
        self.assertEqual(result, expected)

    @mock.patch("apps.main.management.commands.restore_db.sys.exit")
    def test_validate_arguments_target_production(self, mock_exit):
        """
        Test that validate_arguments exits when target is production.
        :param mock_exit:
        :return: None
        """
        self.command.validate_arguments(
            source="local", target="production", file_name="file.dump"
        )
        mock_exit.assert_called_once_with(1)

    @mock.patch("apps.main.management.commands.restore_db.sys.exit")
    def test_validate_arguments_target_not_in_db(self, mock_exit):
        """
        Test that validate_arguments exits when target is not in the database.
        :param mock_exit:
        :return:
        """
        self.command.validate_arguments(
            source="local", target="invalid", file_name="file.dump"
        )
        mock_exit.assert_called_once_with(1)

    @mock.patch("apps.main.management.commands.restore_db.sys.exit")
    def test_validate_arguments_source_not_in_db(self, mock_exit):
        """
        Test that validate_arguments exits when source is not in the database.
        :param mock_exit:
        :return:
        """
        self.command.validate_arguments(
            source="invalid", target="local", file_name="file.dump"
        )
        mock_exit.assert_called_once_with(1)

    @mock.patch("apps.main.management.commands.restore_db.sys.exit")
    def test_validate_arguments_same_source_target(self, mock_exit):
        """
        Test that validate_arguments exits when source and target are the same.
        :param mock_exit:
        :return:
        """
        self.command.validate_arguments(
            source="local", target="local", file_name="file.dump"
        )
        mock_exit.assert_called_once_with(0)

    @mock.patch(
        "apps.main.management.commands.restore_db.os.path.exists", return_value=False
    )
    @mock.patch("apps.main.management.commands.restore_db.sys.exit")
    def test_validate_arguments_file_missing(self, mock_exit, mock_exists):
        """
        Test that validate_arguments exits when file is missing.
        :param mock_exit:
        :param mock_exists:
        :return:
        """
        self.command.validate_arguments(
            source=None, target="local", file_name="missing.dump"
        )
        mock_exit.assert_called_once_with(1)

    @mock.patch("apps.main.management.commands.restore_db.subprocess.check_call")
    @mock.patch(
        "apps.main.management.commands.restore_db.os.path.exists", return_value=True
    )
    def test_command_execution_success(self, mock_exists, mock_subprocess):
        """
        Test that the command executes successfully.
        :param mock_exists:
        :param mock_subprocess:
        :return:
        """
        with mock.patch(
            "apps.main.management.commands.restore_db.input", return_value="y"
        ):
            # Use production as source and local as target (both exist in database_config)
            call_command(
                "restore_db", source="production", target="local", file_name="test.dump"
            )
            mock_subprocess.assert_called()

    @mock.patch("apps.main.management.commands.restore_db.subprocess.check_call")
    @mock.patch(
        "apps.main.management.commands.restore_db.os.path.exists", return_value=True
    )
    def test_same_source_target_error(self, mock_exists, mock_subprocess):
        """
        Test that the command exits when source and target are the same.
        :param mock_exists:
        :param mock_subprocess:
        :return:
        """
        with self.assertRaises(SystemExit):
            call_command(
                "restore_db", source="local", target="local", file_name="test.dump"
            )

    @mock.patch("apps.main.management.commands.restore_db.subprocess.check_call")
    @mock.patch(
        "apps.main.management.commands.restore_db.os.path.exists", return_value=True
    )
    def test_production_target_error(self, mock_exists, mock_subprocess):
        """
        Test that the command exits when target is production.
        :param mock_exists:
        :param mock_subprocess:
        :return:
        """
        with self.assertRaises(SystemExit):
            call_command(
                "restore_db", source="local", target="production", file_name="test.dump"
            )

    @mock.patch(
        "apps.main.management.commands.restore_db.subprocess.check_call",
        side_effect=subprocess.CalledProcessError(1, "cmd"),
    )
    @mock.patch(
        "apps.main.management.commands.restore_db.os.path.exists", return_value=True
    )
    def test_command_execution_failure(self, mock_exists, mock_subprocess):
        """
        Test that the command exits when the command fails.
        :param mock_exists:
        :param mock_subprocess:
        :return:
        """
        with mock.patch(
            "apps.main.management.commands.restore_db.input", return_value="n"
        ):
            with self.assertRaises(SystemExit):
                call_command(
                    "restore_db", source="local", target="local", file_name="test.dump"
                )

    @mock.patch("apps.main.management.commands.restore_db.subprocess.check_call")
    def test_run_commands_success(self, mock_check_call):
        """Test that run_commands executes without errors."""
        commands = ['echo "Test Command"']
        env = {"TEST": "environment"}

        self.command.run_commands(commands, env)

        mock_check_call.assert_called_with(commands[0], env=env, shell=True)

    @mock.patch(
        "subprocess.check_call", side_effect=subprocess.CalledProcessError(1, "cmd")
    )
    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_run_commands_failure(self, mock_stdout, mock_check_call):
        """Test that run_commands handles a failed command."""
        command = Command()
        commands = ["invalid_command"]
        env = {"TEST": "environment"}

        command.run_commands(commands, env)
        self.assertIn("Command failed with error:", mock_stdout.getvalue())

    @override_settings(DEBUG=False)
    @mock.patch(
        "apps.main.management.commands.restore_db.os.path.exists", return_value=True
    )
    @mock.patch("sys.exit")
    @mock.patch("apps.main.management.commands.restore_db.input", return_value="y")
    def test_handle_with_debug_false(self, mock_input, mock_exit, mock_exists):
        """
        Test that the handle method exits when DEBUG is set to False.
        """
        call_command("restore_db")
        mock_exit.assert_called_once_with(1)

    @mock.patch("sys.exit")
    @mock.patch(
        "apps.main.management.commands.restore_db.Command.generate_source_commands",
        return_value=[],
    )
    @mock.patch(
        "apps.main.management.commands.restore_db.Command.generate_target_commands",
        return_value=[],
    )
    @mock.patch("sys.stdout", new_callable=StringIO)
    @mock.patch("apps.main.management.commands.restore_db.input", return_value="y")
    def test_handle_no_commands(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_input,
        mock_stdout,
        mock_target_commands,
        mock_source_commands,
        mock_exit,
    ):
        """
        Test that the handle method exits with no commands message when no commands are available.
        """
        call_command("restore_db", source="production", target="local")
        self.assertIn(NO_COMMANDS_MESSAGE, mock_stdout.getvalue())
        mock_exit.assert_called_once_with(0)

    def test_generate_source_commands_with_source(self):
        """Test that source commands are generated when source is provided."""
        commands = self.command.generate_source_commands("production", "file.dump")
        self.assertEqual(len(commands), 1)
        self.assertIn("pg_dump -Fc -v --host=", commands[0])
        self.assertIn("file.dump", commands[0])

    def test_generate_source_commands_returns_list(self):
        """Test that generate_source_commands returns a list."""
        commands = self.command.generate_source_commands("local", "test.dump")
        self.assertIsInstance(commands, list)
        self.assertEqual(len(commands), 1)

    def test_generate_target_commands_with_drop_and_restore(self):
        """Test target commands generation with drop and restore flags."""
        kwargs = {"drop": True, "restore": True}
        commands = self.command.generate_target_commands("local", kwargs, "test.dump")

        # Should have 3 commands: drop tables, setup, and restore
        self.assertEqual(len(commands), 3)
        self.assertIn("drop_tables.sql", commands[0])
        self.assertIn("setup.sql", commands[1])
        self.assertIn("pg_restore", commands[2])

    def test_generate_target_commands_with_restore_only(self):
        """Test target commands generation with only restore flag."""
        kwargs = {"drop": False, "restore": True}
        commands = self.command.generate_target_commands("local", kwargs, "test.dump")

        # Should have 2 commands: setup and restore (no drop)
        self.assertEqual(len(commands), 2)
        self.assertIn("setup.sql", commands[0])
        self.assertIn("pg_restore", commands[1])

    def test_generate_target_commands_no_restore(self):
        """Test target commands generation with no restore flag."""
        kwargs = {"drop": False, "restore": False}
        commands = self.command.generate_target_commands("local", kwargs, "test.dump")

        # Should have 0 commands
        self.assertEqual(len(commands), 0)

    @override_settings(DEBUG=True)
    @mock.patch(
        "apps.main.management.commands.restore_db.sys.exit",
        side_effect=SystemExit,
    )
    @mock.patch("apps.main.management.commands.restore_db.input", return_value="n")
    @mock.patch("apps.main.management.commands.restore_db.Command.run_commands")
    @mock.patch(
        "apps.main.management.commands.restore_db.Command.generate_source_commands",
        return_value=["echo source"],
    )
    @mock.patch(
        "apps.main.management.commands.restore_db.Command.generate_target_commands",
        return_value=["echo target"],
    )
    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_handle_user_declines_confirmation(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_stdout,
        mock_generate_target,
        mock_generate_source,
        mock_run_commands,
        mock_input,
        mock_exit,
    ) -> None:
        """
        Test that the command exits gracefully when the user declines confirmation.
        """
        with self.assertRaises(SystemExit):
            call_command(
                "restore_db",
                source="production",
                target="local",
                no_input=False,
            )

        self.assertIn("Exiting now", mock_stdout.getvalue())
        mock_exit.assert_called_once_with(0)
        mock_run_commands.assert_not_called()
