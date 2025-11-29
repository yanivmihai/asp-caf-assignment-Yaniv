from pathlib import Path
from shutil import rmtree

from libcaf.constants import DEFAULT_BRANCH, HASH_LENGTH
from libcaf.plumbing import hash_object, load_commit, load_tree
from libcaf.ref import RefError, SymRef
from libcaf.repository import HashRef, Repository, RepositoryError, branch_ref
from pytest import raises

import pytest
from libcaf.repository import RepositoryError


def test_init_with_custom_repo_dir(temp_repo_dir: Path) -> None:
    custom_repo_dir = '.custom_caf'
    repo = Repository(temp_repo_dir, custom_repo_dir)

    assert repo.repo_dir.name == custom_repo_dir
    assert str(repo.repo_dir) == custom_repo_dir

    repo.init()
    assert repo.exists()
    assert (temp_repo_dir / custom_repo_dir).exists()


def test_commit(temp_repo: Repository) -> None:
    temp_file = temp_repo.working_dir / 'test_file.txt'
    temp_file.write_text('This is a test file for commit.')

    author, message = 'John Doe', 'Initial commit'

    assert temp_repo.head_ref() == branch_ref(DEFAULT_BRANCH)

    commit_ref = temp_repo.commit_working_dir(author, message)
    commit = load_commit(temp_repo.objects_dir(), commit_ref)

    assert commit.author == author
    assert commit.message == message
    assert commit.tree_hash is not None

    # Check that HEAD remains pointing to the branch
    # and that the branch points to the commit
    assert temp_repo.head_ref() == branch_ref(DEFAULT_BRANCH)
    assert temp_repo.head_commit() == commit_ref

    commit_object = temp_repo.objects_dir() / commit_ref[:2] / commit_ref
    assert commit_object.exists()


def test_commit_with_parent(temp_repo: Repository) -> None:
    objects_dir = temp_repo.objects_dir()

    temp_file = temp_repo.working_dir / 'test_file.txt'
    temp_file.write_text('Initial commit content')
    temp_repo.save_file_content(temp_file)

    first_commit_ref = temp_repo.commit_working_dir('John Doe', 'First commit')
    first_commit = load_commit(objects_dir, first_commit_ref)

    assert first_commit_ref == hash_object(first_commit)
    assert temp_repo.head_commit() == first_commit_ref

    temp_file.write_text('Second commit content')
    temp_repo.save_file_content(temp_file)

    second_commit_ref = temp_repo.commit_working_dir('John Doe', 'Second commit')
    second_commit = load_commit(objects_dir, second_commit_ref)

    assert second_commit_ref == hash_object(second_commit)
    assert temp_repo.head_commit() == second_commit_ref

    assert second_commit.parent == first_commit_ref


def test_save_dir(temp_repo: Repository) -> None:
    test_dir = temp_repo.working_dir / 'test_dir'
    test_dir.mkdir()
    sub_dir = test_dir / 'sub_dir'
    sub_dir.mkdir()

    file1 = test_dir / 'file1.txt'
    file1.write_text('Content of file1')
    file2 = sub_dir / 'file2.txt'
    file2.write_text('Content of file2')
    file3 = sub_dir / 'file3.txt'
    file3.write_text('Content of file3')

    tree_ref = temp_repo.save_dir(test_dir)

    assert isinstance(tree_ref, HashRef)
    assert len(tree_ref) == HASH_LENGTH

    objects_dir = temp_repo.objects_dir()

    for file_path in [file1, file2, file3]:
        file_blob_hash = hash_object(temp_repo.save_file_content(file_path))
        assert (objects_dir / file_blob_hash[:2] / file_blob_hash).exists()

    assert (objects_dir / tree_ref[:2] / tree_ref).exists()


def test_head_log(temp_repo: Repository) -> None:
    temp_file = temp_repo.working_dir / 'commit_test.txt'

    temp_file.write_text('Initial commit')
    commit_ref1 = temp_repo.commit_working_dir('Author', 'First commit')

    temp_file.write_text('Second commit')
    commit_ref2 = temp_repo.commit_working_dir('Author', 'Second commit')

    assert [_.commit_ref for _ in temp_repo.log()] == [commit_ref2, commit_ref1]


def test_refs_directory_not_exists_raises_error(temp_repo: Repository) -> None:
    # Remove the refs directory to trigger the error condition
    refs_dir = temp_repo.refs_dir()
    rmtree(refs_dir)

    # This should raise RepositoryError because refs directory doesn't exist
    with raises(RepositoryError):
        temp_repo.refs()


def test_refs_directory_is_file_raises_error(temp_repo: Repository) -> None:
    refs_dir = temp_repo.refs_dir()

    # Remove refs directory if it exists and create a file with the same name
    rmtree(refs_dir)
    refs_dir.touch()

    # This should raise RepositoryError because refs directory is a file, not a directory
    with raises(RepositoryError):
        temp_repo.refs()


def test_resolve_ref_invalid_string_raises_error(temp_repo: Repository) -> None:
    with raises(RefError):
        temp_repo.resolve_ref('invalid_reference_string')

    with raises(RefError):
        temp_repo.resolve_ref('g' * HASH_LENGTH)  # 'g' is not a valid hex character

    with raises(RefError):
        temp_repo.resolve_ref('abc123')


def test_resolve_ref_invalid_type_raises_error(temp_repo: Repository) -> None:
    with raises(RefError):
        temp_repo.resolve_ref(123)

    with raises(RefError):
        temp_repo.resolve_ref([])

    with raises(RefError):
        temp_repo.resolve_ref({})


def test_update_ref_nonexistent_reference_raises_error(temp_repo: Repository) -> None:
    with raises(RepositoryError):
        temp_repo.update_ref('nonexistent_branch', HashRef('a' * 40))


def test_delete_repo_removes_repository(temp_repo: Repository) -> None:
    repo_path = temp_repo.repo_path()
    assert repo_path.exists()
    assert temp_repo.exists()

    temp_repo.delete_repo()

    assert not repo_path.exists()
    assert not temp_repo.exists()


def test_add_empty_branch_name_raises_error(temp_repo: Repository) -> None:
    with raises(ValueError, match='Branch name is required'):
        temp_repo.add_branch('')


def test_add_branch_already_exists_raises_error(temp_repo: Repository) -> None:
    with raises(RepositoryError):
        temp_repo.add_branch(DEFAULT_BRANCH)


def test_save_dir_invalid_path_raises_error(temp_repo: Repository) -> None:
    with raises(NotADirectoryError):
        temp_repo.save_dir(None)

    test_file = temp_repo.working_dir / 'test_file.txt'
    with raises(NotADirectoryError):
        temp_repo.save_dir(test_file)

    with raises(NotADirectoryError):
        temp_repo.save_dir(temp_repo.working_dir / 'non_existent_dir')


def test_delete_empty_branch_name_raises_error(temp_repo: Repository) -> None:
    with raises(ValueError, match='Branch name is required'):
        temp_repo.delete_branch('')


def test_delete_nonexistent_branch_name_raises_error(temp_repo: Repository) -> None:
    with raises(RepositoryError):
        temp_repo.delete_branch('nonexistent_branch')


def test_delete_last_branch_name_raises_error(temp_repo: Repository) -> None:
    with raises(RepositoryError):
        temp_repo.delete_branch('main')


def test_commit_working_dir_empty_author_or_message_raises_error(temp_repo: Repository) -> None:
    with raises(ValueError, match='Author is required'):
        temp_repo.commit_working_dir('', 'Valid message')

    with raises(ValueError, match='Author is required'):
        temp_repo.commit_working_dir(None, 'Valid message')  # type: ignore

    with raises(ValueError, match='Commit message is required'):
        temp_repo.commit_working_dir('Valid author', '')

    with raises(ValueError, match='Commit message is required'):
        temp_repo.commit_working_dir('Valid author', None)  # type: ignore

    with raises(ValueError, match='Author is required'):
        temp_repo.commit_working_dir('', '')


def test_log_corrupted_commit_raises_error(temp_repo: Repository) -> None:
    # First, create a valid commit
    temp_file = temp_repo.working_dir / 'test_file.txt'
    temp_file.write_text('Initial commit content')
    commit_ref = temp_repo.commit_working_dir('Author', 'Test commit')

    # Now corrupt the commit object by writing invalid data to it
    # Overwrite the commit object with invalid content
    objects_dir = temp_repo.objects_dir()
    commit_path = objects_dir / commit_ref[:2] / commit_ref
    commit_path.write_text('corrupted commit data')

    # Attempting to get the log should raise RepositoryError due to the corrupted commit
    with raises(RepositoryError):
        list(temp_repo.log())  # Convert generator to list to force evaluation


def test_diff_commits_corrupted_commit_raises_error(temp_repo: Repository) -> None:
    # First, create two valid commits
    temp_file = temp_repo.working_dir / 'test_file.txt'
    temp_file.write_text('Initial commit content')
    commit_ref1 = temp_repo.commit_working_dir('Author', 'First commit')

    temp_file.write_text('Second commit content')
    commit_ref2 = temp_repo.commit_working_dir('Author', 'Second commit')

    # Now corrupt the first commit object by writing invalid data to it
    # Overwrite the commit object with invalid content
    objects_dir = temp_repo.objects_dir()
    commit_path = objects_dir / commit_ref1[:2] / commit_ref1
    commit_path.write_text('corrupted commit data')

    # Attempting to diff commits should raise RepositoryError due to the corrupted commit
    with raises(RepositoryError):
        temp_repo.diff_commits(commit_ref1, commit_ref2)


def test_diff_commits_corrupted_tree_raises_error(temp_repo: Repository) -> None:
    # First, create two valid commits
    temp_file = temp_repo.working_dir / 'test_file.txt'
    temp_file.write_text('Initial commit content')
    commit_ref1 = temp_repo.commit_working_dir('Author', 'First commit')

    temp_file.write_text('Second commit content')
    commit_ref2 = temp_repo.commit_working_dir('Author', 'Second commit')

    # Load the commits to get their tree hashes
    objects_dir = temp_repo.objects_dir()
    commit1 = load_commit(objects_dir, commit_ref1)

    # Corrupt the tree object of the first commit
    # Overwrite the tree object with invalid content
    tree_hash = commit1.tree_hash
    tree_path = objects_dir / tree_hash[:2] / tree_hash
    tree_path.write_text('corrupted tree data')

    # Attempting to diff commits should raise RepositoryError due to the corrupted tree
    with raises(RepositoryError):
        temp_repo.diff_commits(commit_ref1, commit_ref2)


def test_diff_commits_corrupted_subtree_raises_error(temp_repo: Repository) -> None:
    # Create a directory structure with subdirectories to trigger recursive tree comparison
    test_dir = temp_repo.working_dir / 'test_dir'
    test_dir.mkdir()
    sub_dir = test_dir / 'sub_dir'
    sub_dir.mkdir()

    # Create files in both the main directory and subdirectory
    main_file = temp_repo.working_dir / 'main_file.txt'
    main_file.write_text('Main file content')
    sub_file = sub_dir / 'sub_file.txt'
    sub_file.write_text('Sub file content - version 1')

    # Create first commit
    commit_ref1 = temp_repo.commit_working_dir('Author', 'First commit with subdirectory')

    # Modify the file in the subdirectory to create a different tree
    sub_file.write_text('Sub file content - version 2')

    # Create second commit
    commit_ref2 = temp_repo.commit_working_dir('Author', 'Second commit with modified subdirectory')

    # Load the first commit to access its tree structure
    objects_dir = temp_repo.objects_dir()
    commit1 = load_commit(objects_dir, commit_ref1)

    # Load the root tree to find the subdirectory tree hash
    root_tree = load_tree(objects_dir, commit1.tree_hash)

    # Find the subdirectory tree record
    subdir_tree_hash: str | None = None
    for record in root_tree.records.values():
        if record.name == 'test_dir':
            # Load the test_dir tree to get its subdirectory
            test_dir_tree = load_tree(objects_dir, record.hash)
            for sub_record in test_dir_tree.records.values():
                if sub_record.name == 'sub_dir':
                    subdir_tree_hash = sub_record.hash
                    break
            break

    assert subdir_tree_hash is not None, 'Subdirectory tree hash should not be None'

    # Corrupt the subdirectory tree object
    tree_path = objects_dir / subdir_tree_hash[:2] / subdir_tree_hash
    tree_path.write_text('corrupted subtree data')

    # Attempting to diff commits should raise RepositoryError due to the corrupted subtree
    with raises(RepositoryError):
        temp_repo.diff_commits(commit_ref1, commit_ref2)


def test_head_ref_missing_head_file_raises_error(temp_repo: Repository) -> None:
    # Remove the HEAD file to trigger the error condition
    temp_repo.head_file().unlink()

    # Attempting to get head_ref should raise RepositoryError due to missing HEAD file
    with raises(RepositoryError):
        temp_repo.head_ref()


def test_head_commit_with_symbolic_ref_returns_hash_ref(temp_repo: Repository) -> None:
    # First, create a commit so we have something to point to
    temp_file = temp_repo.working_dir / 'test_file.txt'
    temp_file.write_text('Test content')
    commit_ref = temp_repo.commit_working_dir('Author', 'Test commit')
    assert isinstance(commit_ref, HashRef)

    # Verify that HEAD is a symbolic reference pointing to a branch
    head_ref = temp_repo.head_ref()
    assert isinstance(head_ref, SymRef)

    # Update the HEAD to point to the commit we just created
    temp_repo.update_ref('heads/main', commit_ref)

    assert temp_repo.head_commit() == commit_ref




# --- Tag tests ---


def test_list_tags_empty_repo(temp_repo: Repository) -> None:
    """Tags list should be empty in a fresh repo."""
    assert temp_repo.list_tags() == []


def test_create_and_list_tags(temp_repo: Repository, tmp_path) -> None:
    """Creating tags should persist them under refs/tags and list_tags should see them."""
    # Create a commit
    file_path = temp_repo.working_dir / "file.txt"
    file_path.write_text("content")
    commit_ref = temp_repo.commit_working_dir("Tester", "Initial commit")

    # Create two tags pointing to the same commit
    temp_repo.create_tag("v1.0.0", commit_ref)
    temp_repo.create_tag("release", "HEAD")

    tags = temp_repo.list_tags()
    # list_tags returns tags sorted lexicographically
    assert tags == ["release", "v1.0.0"]


def test_create_tag_duplicate_name_raises(temp_repo: Repository) -> None:
    """Creating a tag with an existing name should raise a RepositoryError."""
    file_path = temp_repo.working_dir / "file.txt"
    file_path.write_text("content")
    temp_repo.commit_working_dir("Tester", "Initial commit")

    temp_repo.create_tag("v1.0.0", "HEAD")

    with pytest.raises(RepositoryError):
        temp_repo.create_tag("v1.0.0", "HEAD")


def test_create_tag_invalid_commit_raises(temp_repo: Repository) -> None:
    """Creating a tag pointing to a non-existent commit should raise."""
    # 40 hex chars, looks like a hash but does not exist in the repo
    bogus_hash = "deadbeef" * 5

    with pytest.raises(RepositoryError):
        temp_repo.create_tag("bad-tag", bogus_hash)


def test_delete_tag_removes_it(temp_repo: Repository) -> None:
    """Deleting an existing tag should remove it from disk and from list_tags()."""
    file_path = temp_repo.working_dir / "file.txt"
    file_path.write_text("content")
    temp_repo.commit_working_dir("Tester", "Initial commit")

    temp_repo.create_tag("to-delete", "HEAD")
    assert "to-delete" in temp_repo.list_tags()

    temp_repo.delete_tag("to-delete")
    assert "to-delete" not in temp_repo.list_tags()


def test_delete_nonexistent_tag_raises(temp_repo: Repository) -> None:
    """Deleting a non-existent tag should raise a RepositoryError."""
    with pytest.raises(RepositoryError):
        temp_repo.delete_tag("no-such-tag")