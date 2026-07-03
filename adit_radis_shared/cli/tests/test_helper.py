from pathlib import Path

from adit_radis_shared.cli.helper import CommandHelper


def create_helper_with_env_file(tmp_path: Path, content: str) -> CommandHelper:
    (tmp_path / ".env").write_text(content)
    helper = CommandHelper()
    helper.root_path = tmp_path
    return helper


def test_find_quoted_env_file_keys_reports_quoted_values(tmp_path: Path):
    helper = create_helper_with_env_file(
        tmp_path,
        (
            "FOO=unquoted value\n"
            'DOUBLE_QUOTED="some value"\n'
            "SINGLE_QUOTED='some value'\n"
            'TRAILING_COMMENT="some value" # a comment\n'
            "EMPTY=\n"
            "# COMMENTED=\"some value\"\n"
        ),
    )

    assert helper.find_quoted_env_file_keys() == [
        "DOUBLE_QUOTED",
        "SINGLE_QUOTED",
        "TRAILING_COMMENT",
    ]


def test_find_quoted_env_file_keys_passes_unquoted_values(tmp_path: Path):
    helper = create_helper_with_env_file(
        tmp_path,
        (
            "BACKUP_CRON=0 3 * * *\n"
            "SITE_NAME=Example Project\n"
            "DJANGO_EMAIL_URL=smtp://localhost:25\n"
        ),
    )

    assert helper.find_quoted_env_file_keys() == []
