import os
from unittest import mock

from vs_data_api import env


def write_env(tmp_path, text, name=".env"):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_loads_quoted_and_exported_values(tmp_path):
    path = write_env(
        tmp_path,
        'VSDATA_TEST_ENVFILE_QUOTED="Driver={FileMaker ODBC};Server=localhost;PWD=1234"\n'
        "export VSDATA_TEST_ENVFILE_EXPORT='single quoted'\n"
        "VSDATA_TEST_ENVFILE_PLAIN=plain\n",
    )
    with mock.patch.dict(os.environ, {env.ENV_FILE_VAR: str(path)}):
        assert env.load_env_file() == path
        # surrounding quotes are not part of the value (the nssm trap)
        assert os.environ["VSDATA_TEST_ENVFILE_QUOTED"] == "Driver={FileMaker ODBC};Server=localhost;PWD=1234"
        assert os.environ["VSDATA_TEST_ENVFILE_EXPORT"] == "single quoted"
        assert os.environ["VSDATA_TEST_ENVFILE_PLAIN"] == "plain"
        for key in ("VSDATA_TEST_ENVFILE_QUOTED", "VSDATA_TEST_ENVFILE_EXPORT", "VSDATA_TEST_ENVFILE_PLAIN"):
            del os.environ[key]


def test_real_environment_wins_over_file(tmp_path):
    path = write_env(tmp_path, "VSDATA_TEST_ENVFILE_WINS=from_file\n")
    with mock.patch.dict(os.environ, {env.ENV_FILE_VAR: str(path), "VSDATA_TEST_ENVFILE_WINS": "from_shell"}):
        env.load_env_file()
        assert os.environ["VSDATA_TEST_ENVFILE_WINS"] == "from_shell"


def test_explicit_file_is_the_only_one_loaded(tmp_path, monkeypatch):
    explicit = write_env(tmp_path, "VSDATA_TEST_ENVFILE_X=explicit\n", name="custom.env")
    write_env(tmp_path, "VSDATA_TEST_ENVFILE_Y=cwd\n")
    monkeypatch.chdir(tmp_path)
    with mock.patch.dict(os.environ, {env.ENV_FILE_VAR: str(explicit)}):
        assert env.env_file_candidates() == [explicit]
        env.load_env_file()
        assert "VSDATA_TEST_ENVFILE_Y" not in os.environ
        del os.environ["VSDATA_TEST_ENVFILE_X"]


def test_missing_file_is_not_an_error(tmp_path):
    with mock.patch.dict(os.environ, {env.ENV_FILE_VAR: str(tmp_path / "nope.env")}):
        assert env.load_env_file() is None
