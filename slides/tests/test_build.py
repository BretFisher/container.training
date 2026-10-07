"""Check build selection without compiling decks or changing the checkout."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SLIDES = Path(__file__).resolve().parents[1]
MAKE = shutil.which("make")


class BuildSelectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        shutil.copyfile(SLIDES / "build.sh", self.work / "build.sh")
        shutil.copyfile(SLIDES / "Makefile", self.work / "Makefile")
        (self.work / "build.sh").chmod(0o755)
        for name in ("a.yml", "b.yml"):
            (self.work / name).write_text("fixture\n")
        self.executable("index.py", 'echo index >> trace; echo catalog > index.html')
        self.executable("markmaker.py", 'if [ "$1" = --reference ]; then echo "reference" > "$2"; shift 2; fi; '
                        'printf "compile %s\\n" "$1" >> trace; echo "HTML for $1"')
        (self.work / "bin").mkdir()
        self.executable("bin/zip", 'echo zip >> trace; touch slides.zip')

    def executable(self, name, body):
        path = self.work / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def build(self, deck="", action="once", archive=False):
        env = dict(os.environ, SLIDES_DECK=deck, SLIDES_ZIP="1" if archive else "",
                   PATH=str(self.work / "bin") + os.pathsep + os.environ["PATH"])
        return subprocess.run(["sh", "build.sh", action], cwd=self.work, env=env,
                              capture_output=True, text=True)

    def trace(self):
        path = self.work / "trace"
        return path.read_text().splitlines() if path.exists() else []

    def test_default_builds_catalog_and_all_decks(self):
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Building all decks.", result.stdout)
        self.assertEqual(self.trace(), ["index", "compile a.yml", "compile b.yml"])
        self.assertTrue((self.work / "b.yml.html").exists())
        self.assertTrue((self.work / "b.reference.yml.html").exists())

    def test_selected_build_leaves_catalog_and_other_decks_unchanged(self):
        (self.work / "index.html").write_text("old catalog")
        (self.work / "b.yml.html").write_text("old deck")
        result = self.build("a.yml")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Building deck: a.yml", result.stdout)
        self.assertEqual(self.trace(), ["compile a.yml"])
        self.assertEqual((self.work / "index.html").read_text(), "old catalog")
        self.assertEqual((self.work / "b.yml.html").read_text(), "old deck")
        self.assertIn("a.yml", (self.work / "a.yml.html").read_text())

    def test_invalid_selection_fails_before_any_output_changes(self):
        sentinel = self.work / "a.yml.html.tmp"
        for deck in ("missing.yml", "../a.yml", "-a.yml", "a.yaml", "a.yml;touch injected", "$(touch injected).yml"):
            with self.subTest(deck=deck):
                sentinel.write_text("keep")
                result = self.build(deck)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue("Deck not found" in result.stderr or "Invalid SLIDES_DECK" in result.stderr)
                self.assertEqual(self.trace(), [])
                self.assertEqual(sentinel.read_text(), "keep")
                self.assertFalse((self.work / "injected").exists())

    def test_check_validates_without_building(self):
        result = self.build("a.yml", action="check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Building", result.stdout)
        self.assertEqual(self.trace(), [])
        self.assertNotEqual(self.build("missing.yml", action="check").returncode, 0)

    def test_archive_builds_all_decks_despite_selector(self):
        result = self.build("a.yml", archive=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Building all decks.", result.stdout)
        self.assertNotIn("Building deck:", result.stdout)
        self.assertEqual(self.trace(), ["index", "compile a.yml", "compile b.yml", "zip"])
        self.assertTrue((self.work / "slides.zip").exists())

    @unittest.skipUnless(MAKE, "Make is needed to test its selector export")
    def test_make_uses_canonical_selector_from_argument_or_environment(self):
        self.executable("bin/docker", 'printf "Compose selector=%s\\n" "$SLIDES_DECK"')
        self.executable("bin/python3", 'printf "Lab arguments=%s\\n" "$*"')
        for selector, argument in (("", False), ("a.yml", False), ("b.yml", True)):
            with self.subTest(selector=selector, argument=argument):
                env = dict(os.environ, SLIDES_DECK="", REPOSITORY_URL="test",
                           BRANCH="test", COMMIT="test",
                           PATH=str(self.work / "bin") + os.pathsep + os.environ["PATH"])
                args = [MAKE, "--no-print-directory", "-s", "serve"]
                if argument:
                    # A Make argument must override an exported selection.
                    env["SLIDES_DECK"] = "a.yml"
                    args.append("SLIDES_DECK=" + selector)
                else:
                    env["SLIDES_DECK"] = selector
                result = subprocess.run(args, cwd=self.work, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                banner = "Serving deck: " + selector if selector else "Serving all decks."
                self.assertEqual(result.stdout.splitlines(), [banner, "Compose selector=" + selector])
                result = subprocess.run([MAKE, "--no-print-directory", "-s", "labtest-plan"] +
                                        (["SLIDES_DECK=" + selector] if argument else []),
                                        cwd=self.work, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("plan " + (selector or "kube-sec-twodays.yml"), result.stdout)
