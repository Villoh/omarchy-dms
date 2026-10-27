"""The release body generator (.github/scripts/release_body.py), run as the workflow runs it."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "release_body.py"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "GITHUB_REPOSITORY": "o/r",
}


class ReleaseBodyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.git("init", "-q")
        (self.repo / ".github" / "scripts").mkdir(parents=True)
        (self.repo / ".github" / "scripts" / "release_body.py").write_text(SCRIPT.read_text())
        (self.repo / ".github" / "release-notes").mkdir()
        (self.repo / ".github" / "release-notes" / "_install.md").write_text("## Install\n{tag} {version}\n")

    def git(self, *args):
        # Isolated from the user's git config (signing, editors): plain commits and lightweight tags.
        opts = ["-c", "commit.gpgsign=false", "-c", "tag.gpgSign=false", "-c", "tag.forceSignAnnotated=false"]
        subprocess.run(["git", *opts, *args], cwd=self.repo, check=True, env=ENV)

    def commit(self, subject, body=""):
        self.git("commit", "-q", "--allow-empty", "-m", subject, "-m", body)

    def body(self, tag, *flags):
        script = self.repo / ".github" / "scripts" / "release_body.py"
        r = subprocess.run(
            ["python3", str(script), tag, *flags], cwd=self.repo, capture_output=True, text=True, env=ENV
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_groups_commits_since_the_previous_tag(self):
        self.commit("feat: first")
        self.git("tag", "v0.1.0")
        self.commit("feat(cli): new thing")
        self.commit("fix: broken thing")
        self.commit("docs: explain")
        self.commit("ci: tweak workflow")
        self.commit("chore: release 0.2.0")
        self.commit("not conventional")
        self.commit("feat!: drop a flag")
        self.git("tag", "v0.2.0")
        out = self.body("v0.2.0")
        self.assertNotIn("first", out)  # belongs to the previous release
        self.assertNotIn("chore: release", out)
        self.assertLess(out.index("### Breaking changes"), out.index("### Features"))
        self.assertLess(out.index("### Features"), out.index("### Bug fixes"))
        self.assertIn("- **cli:** new thing", out)
        self.assertIn("### Other changes\n- not conventional", out)
        self.assertIn("<summary>Maintenance</summary>", out)
        self.assertIn("tweak workflow", out)
        self.assertIn("**Full Changelog**: https://github.com/o/r/compare/v0.1.0...v0.2.0", out)
        self.assertTrue(out.rstrip().endswith("v0.2.0 0.2.0"))  # the fixed section, substituted

    def test_first_release_has_no_previous_tag(self):
        self.commit("feat: initial release")
        self.git("tag", "v0.1.0")
        out = self.body("v0.1.0")
        self.assertIn("- initial release", out)
        self.assertNotIn("Full Changelog", out)

    def test_breaking_footer_and_hand_written_notes(self):
        self.commit("feat: a")
        self.git("tag", "v0.1.0")
        self.commit("refactor: b", "BREAKING CHANGE: renamed")
        self.git("tag", "v0.2.0")
        self.assertIn("### Breaking changes\n- b", self.body("v0.2.0"))
        (self.repo / ".github" / "release-notes" / "v0.2.0.md").write_text("Hand written.\n")
        out = self.body("v0.2.0")
        self.assertTrue(out.startswith("Hand written."))
        self.assertIn("## Install", out)
        self.assertIn("### Breaking changes", self.body("v0.2.0", "--generated"))


if __name__ == "__main__":
    unittest.main()
