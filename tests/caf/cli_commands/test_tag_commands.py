from pathlib import Path

from libcaf.repository import Repository
from pytest import CaptureFixture

from caf import cli_commands


def test_tags_no_repo(temp_repo_dir: Path, capsys: CaptureFixture[str]) -> None:
    assert cli_commands.tags(working_dir_path=temp_repo_dir) == -1

    err = capsys.readouterr().err
    assert 'No repository found' in err


def test_tags_empty_repo(temp_repo: Repository, capsys: CaptureFixture[str]) -> None:
    assert cli_commands.tags(working_dir_path=temp_repo.working_dir) == 0

    out = capsys.readouterr().out
    assert 'No tags found' in out


def test_create_tag_command(temp_repo: Repository, capsys: CaptureFixture[str]) -> None:
    # Create a commit to tag
    commit_ref = temp_repo.commit_working_dir('Tester', 'Initial commit')

    capsys.readouterr()

    # Use the CLI to create the tag
    assert cli_commands.create_tag(
        working_dir_path=temp_repo.working_dir,
        tag_name='v1.0.0',
        commit_hash=str(commit_ref),
    ) == 0

    out = capsys.readouterr().out
    assert 'Tag "v1.0.0" created.' in out

    # Verify tag exists via Repository API
    assert temp_repo.list_tags() == ['v1.0.0']


def test_create_tag_missing_name(temp_repo: Repository, capsys: CaptureFixture[str]) -> None:
    commit_ref = temp_repo.commit_working_dir('Tester', 'Initial commit')

    capsys.readouterr()

    assert cli_commands.create_tag(
        working_dir_path=temp_repo.working_dir,
        commit_hash=str(commit_ref),
    ) == -1

    err = capsys.readouterr().err
    assert 'Tag name is required.' in err


def test_create_tag_invalid_commit(temp_repo: Repository, capsys: CaptureFixture[str]) -> None:
    capsys.readouterr()

    # Commit hash does not exist in this repo
    assert cli_commands.create_tag(
        working_dir_path=temp_repo.working_dir,
        tag_name='v1.0.0',
        commit_hash='0' * 40,
    ) == -1

    err = capsys.readouterr().err
    assert 'Repository error' in err


def test_create_tag_duplicate_name(temp_repo: Repository, capsys: CaptureFixture[str]) -> None:
    commit_ref = temp_repo.commit_working_dir('Tester', 'Initial commit')
    temp_repo.create_tag('v1.0.0', commit_ref)

    capsys.readouterr()

    # Second creation with same name should fail
    assert cli_commands.create_tag(
        working_dir_path=temp_repo.working_dir,
        tag_name='v1.0.0',
        commit_hash=str(commit_ref),
    ) == -1

    err = capsys.readouterr().err
    assert 'Repository error' in err

    # Tag list should still contain exactly one tag
    assert temp_repo.list_tags() == ['v1.0.0']


def test_delete_tag_removes_it(temp_repo: Repository, capsys: CaptureFixture[str]) -> None:
    commit_ref = temp_repo.commit_working_dir('Tester', 'Initial commit')
    temp_repo.create_tag('v1.0.0', commit_ref)

    capsys.readouterr()

    assert cli_commands.delete_tag(
        working_dir_path=temp_repo.working_dir,
        tag_name='v1.0.0',
    ) == 0

    out = capsys.readouterr().out
    assert 'Tag "v1.0.0" deleted.' in out
    assert temp_repo.list_tags() == []


def test_delete_nonexistent_tag_raises(temp_repo: Repository, capsys: CaptureFixture[str]) -> None:
    capsys.readouterr()

    assert cli_commands.delete_tag(
        working_dir_path=temp_repo.working_dir,
        tag_name='does_not_exist',
    ) == -1

    err = capsys.readouterr().err
    assert 'Repository error' in err


def test_delete_tag_no_repo(temp_repo_dir: Path, capsys: CaptureFixture[str]) -> None:
    capsys.readouterr()

    assert cli_commands.delete_tag(
        working_dir_path=temp_repo_dir,
        tag_name='v1.0.0',
    ) == -1

    err = capsys.readouterr().err
    assert 'No repository found' in err
