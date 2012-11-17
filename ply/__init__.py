import re
import os

from ply import git


RE_PATCH_IDENTIFIER = re.compile('Ply-Patch: (.*)')


class Repo(object):
    def __init__(self, path):
        self.git_repo = git.Repo(path)

    @property
    def path(self):
        return os.path.abspath(self.git_repo.path)


class WorkingRepo(Repo):
    """Represents our local fork of the upstream repository.

    This is where we will create new patches (save) or apply previous patches
    to create a new patch-branch (restore).
    """
    def format_patches(self, since):
        """Create patch files since a given commmit."""
        filenames = self.git_repo.format_patch(since)

        if not filenames:
            raise Exception('no patch files generated')

        # Remove number prefix from patch filename since we use a `series`
        # file (like quilt) to order the patches
        patch_paths = []
        for filename in filenames:
            orig_path = os.path.join(self.path, filename)
            new_filename = filename.split('-', 1)[1]
            new_path = os.path.join(self.path, new_filename)
            os.rename(orig_path, new_path)

            patch_paths.append(new_path)

        return patch_paths

    def applied_patches(self):
        """Return a list of patches that have already been applied to this
        branch.
        """
        applied = []
        skip = 0
        while True:
            commit_msg = ply.working_repo.git_repo.log(
                    count=1, pretty='%B', skip=skip)
            matches = re.search(RE_PATCH_IDENTIFIER, commit_msg)
            if not matches:
                break

            patch_name = matches.group(1)
            applied.append(patch_name)
            skip += 1

        return applied

    def apply_patches(self, base_path, patch_names, three_way_merge=True):
        """Applies a series of patches to the working repo's current branch.

        Each patch applied creates a commit in the working repo.

        The commit contains a patch identification line which allows us to tie
        it back to a specific patch in the series file. This is used when
        resovling conflicts because it allows us to skip patches that have
        already been applied.
        """
        applied = self.applied_patches()

        for patch_name in patch_names:
            if patch_name in applied:
                continue

            patch_path = os.path.join(base_path, patch_name)
            self.git_repo.am(patch_path, three_way_merge=three_way_merge)

            # Add patch identifier line to commit msg
            commit_msg = ply.working_repo.git_repo.log(
                    count=1, pretty='%B')
            commit_msg += '\n\nPly-Patch: %s' % patch_name
            self.git_repo.commit(commit_msg, amend=True)


class PatchRepo(Repo):
    """Represents a git repo containing versioned patch files."""
    @property
    def series_path(self):
        return os.path.join(self.path, 'series')

    def add_patches(self, patch_paths, quiet=True):
        """Adds and commits a set of patches into the patch repo."""
        with open(self.series_path, 'a') as f:
            for orig_patch_path in patch_paths:
                filename = os.path.basename(orig_patch_path)

                patch_path = os.path.join(self.path, filename)
                if os.path.exists(patch_path):
                    name, ext = patch_path.rsplit('.', 1)
                    for dedup in xrange(999):
                        filename = "%s-%d.%s" % (name, dedup + 1, ext)
                        patch_path = os.path.join(self.path, filename)
                        if not os.path.exists(patch_path):
                            break

                os.rename(orig_patch_path, patch_path)
                self.git_repo.add(filename)
                f.write('%s\n' % filename)

        self.git_repo.add('series')

        # TODO: improve this commit msg, for 1 or 2 patches use short form of
        # just comma separated, for more than that, use long-form of number of
        # patches one first-line and filenames enumerated in the body of
        # commit msg.
        self.git_repo.commit('Adding patches', quiet=quiet)

    def get_patch_names(self):
        with open(self.series_path, 'r') as f:
            for line in f:
                patch_name = line.strip()
                yield patch_name

    def init(self):
        """Initialize the patch repo.

        This performs a git init, adds the series file, and then commits it.
        """
        self.git_repo.init('.')

        if not os.path.exists(self.series_path):
            with open(self.series_path, 'w') as f:
                pass

        self.git_repo.add('series')
        self.git_repo.commit('Ply init')


class Ply(object):
    def __init__(self):
        self.working_repo = WorkingRepo('sandbox/working-repo')
        self.patch_repo = PatchRepo('sandbox/patch-repo')

    def save(self, since, quiet=True):
        """Saves a range of commits into the patch-repo.

        1. Create the patches (using `git format-patch`)
        2. Move the patches into the patch-repo (handling any dups)
        3. Update the `series` file in the patch-repo
        4. Commit the new patches
        """
        patch_paths = self.working_repo.format_patches(since)
        self.patch_repo.add_patches(patch_paths, quiet=quiet)

    def restore(self, three_way_merge=True):
        patch_names = self.patch_repo.get_patch_names()
        self.working_repo.apply_patches(self.patch_repo.path, patch_names)

    def applied_patches(self):
        return self.working_repo.applied_patches()

    def init_patch_repo(self):
        return self.patch_repo.init()


if __name__ == "__main__":
    ply = Ply()
    ply.save('HEAD^1', quiet=False)
    ply.working_repo.git_repo.reset('HEAD^1', hard=True)
    ply.restore()
    print ply.applied_patches()
