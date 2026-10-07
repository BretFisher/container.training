"""Build real HTML in temporary directories; leave the checkout untouched."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


SLIDES = Path(__file__).resolve().parents[1]


class NamedSectionsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        for name in ("workshop.html", "interstitials.txt"):
            shutil.copyfile(SLIDES / name, self.work / name)
        (self.work / "toc.md").write_text("\n@@TOC@@\n")
        (self.work / "first.md").write_text(
            "# Alpha\n\nFirst content.\n\n---\n\n# Beta\n\nSecond content.\n")
        (self.work / "last.md").write_text("# Gamma\n\nLast content.\n")
        (self.work / "intro.md").write_text("## Introduction\n\nNo lecture heading.\n")

    def build(self, content, single=False, dev=False, success=True, prepend_toc=True):
        manifest = {"title": "Test deck", "content": (["toc.md"] if prepend_toc else []) + content,
                    "exclude": ["hidden"]}
        if single:
            manifest["toc"] = "single"
        (self.work / "deck.yml").write_text(yaml.safe_dump(manifest, sort_keys=False))
        env = dict(os.environ, SLIDES_DEV="1" if dev else "0",
                   REPOSITORY_URL="https://example.com/training", BRANCH="test",
                   COMMIT="test")
        result = subprocess.run([sys.executable, str(SLIDES / "markmaker.py"), "deck.yml"],
                                cwd=self.work, env=env, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Invalid content", result.stdout)
            self.assertNotIn("@@TOC@@", result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result.stdout if success else result.stderr

    def test_names_change_only_toc_labels(self):
        old = [["first.md"], ["last.md"]]
        named = [{"title": "Basics", "content": ["first.md"]},
                 {"title": "Deployment", "content": ["last.md"]}]
        for single in (False, True):
            for dev in (False, True):
                with self.subTest(single=single, dev=dev):
                    before = self.build(old, single, dev)
                    after = self.build(named, single, dev)
                    expected = before.replace("Section 1", "Basics").replace("Section 2", "Deployment")
                    self.assertEqual(after, expected)
                    self.assertEqual(after.count("\n---\n"), before.count("\n---\n"))
                    self.assertEqual(re.findall(r"^name: (.*)$", after, re.M),
                                     re.findall(r"^name: (.*)$", before, re.M))
                    self.assertEqual(after.count("class: title"), 3)
                    self.assertEqual(after.count("class: pic"), 3)
                    self.assertNotIn("name: toc-basics", after)

    def test_mixed_groups_standalone_and_navigation(self):
        content = ["intro.md", "first.md", {"title": "Deployment", "content": ["last.md"]}]
        for single in (False, True):
            with self.subTest(single=single):
                html = self.build(content, single)
                self.assertIn("**Section 1**" if single else "## Section 1", html)
                self.assertIn("**Deployment**" if single else "## Deployment", html)
                links = re.findall(r"^- \[([^]]+)\]\(#toc-[^)]+\)$", html, re.M)
                self.assertEqual(links, (["Table of contents"] if not single else []) + ["Alpha", "Beta", "Gamma"])
                self.assertIn("[Previous lecture](#toc-beta)", html)
                self.assertIn("[Next lecture](#toc-gamma)", html)
                self.assertIn("[Previous lecture]({})".format("#toc" if single else "#toc-section-1"), html)
                self.assertIn("[Next lecture]({})".format("#toc" if single else "#toc-section-2"), html)
                self.assertNotIn("[Previous Section]", html)
                self.assertNotIn("[Next Section]", html)
                self.assertIn("[Table of Contents](#toc)" if single else
                              "[Table of Contents](#toc-section-2)", html)

    def test_nested_names_flatten_without_new_hierarchy(self):
        old = [["first.md", ["last.md"]]]
        named = [{"title": "Outer", "content": ["first.md",
                  {"title": "Inner", "content": ["last.md"]}]}]
        for single in (False, True):
            with self.subTest(single=single):
                before = self.build(old, single)
                after = self.build(named, single)
                expected = before.replace("**Section 1**", "**Outer**") if single else before.replace(
                    "## Table of contents", "## Outer")
                self.assertEqual(after, expected)
                self.assertNotIn("Inner", after)
                unnamed_outer = self.build([["first.md", {"title": "Inner", "content": ["last.md"]}]], single)
                self.assertEqual(unnamed_outer, before)

    def test_empty_named_groups_show_labels_without_extra_slides_or_anchors(self):
        for single in (False, True):
            for children in ([], ["intro.md"]):
                with self.subTest(single=single, children=children):
                    old = self.build(([children] if children else []) + ["first.md", ["last.md"]], single)
                    named = self.build([{"title": "Intro", "content": children},
                                        "first.md", {"title": "Middle", "content": []},
                                        ["last.md"], {"title": "End", "content": []}], single)
                    for label in ("Intro", "Middle", "End"):
                        self.assertIn("**" + label + "**" if single else "## " + label, named)
                        self.assertNotIn("name: toc-" + label.lower(), named)
                    self.assertEqual(named.count("\n---\n"), old.count("\n---\n"))
                    self.assertEqual(re.findall(r"^name: .*", named, re.M), re.findall(r"^name: .*", old, re.M))
                    self.assertEqual(re.findall(r"\[Table of Contents\]\([^)]*\)", named),
                                     re.findall(r"\[Table of Contents\]\([^)]*\)", old))
                    self.assertNotIn("Section 3", named)

    def test_only_empty_named_groups_and_nested_empty_labels(self):
        for single in (False, True):
            with self.subTest(single=single):
                html = self.build([{"title": "Intro", "content": []},
                                   {"title": "Resources", "content": ["intro.md"]}], single)
                self.assertIn("**Intro**" if single else "## Intro", html)
                self.assertIn("**Resources**" if single else "## Resources", html)
                self.assertNotIn("class: title", html)
                self.assertNotIn("class: pic", html)
                self.assertEqual(len(re.findall(r"^name: toc(?:-section-1)?$", html, re.M)), 1)
                nested = self.build([[{"title": "Inner", "content": []}], "first.md"], single)
                old = self.build(["first.md"], single)
                self.assertEqual(nested, old)

    def test_invalid_named_groups_fail_clearly(self):
        for group, message in [({"title": "", "content": []}, "single-line title"),
                               ({"title": "Bad\nName", "content": []}, "single-line title"),
                               ({"title": 42, "content": []}, "single-line title"),
                               ({"title": "Basics", "content": "first.md"}, "content list")]:
            with self.subTest(group=group):
                self.assertIn(message, self.build([group], success=False))

    def test_title_footer_is_compact_in_dev_and_keeps_published_build_info(self):
        # Put the real shared title first, as in the workshop. The helper's
        # first file is toc.md, so give that fixture the shared title content.
        (self.work / "toc.md").write_text((SLIDES / "shared/title.md").read_text())
        dev_html = self.build(["first.md"], dev=True)
        self.assertIn("class: title, in-person", dev_html)
        self.assertIn(".debug[toc.md]", dev_html)
        self.assertNotIn("These slides have been built from commit", dev_html)
        self.assertNotIn("git status unavailable", dev_html)
        self.assertIn("class: pic", dev_html)
        self.assertIn("#toc-alpha", dev_html)
        published = self.build(["first.md"], dev=False)
        self.assertIn("These slides have been built from commit: test", published)

    def test_dev_skips_git_and_production_keeps_metadata_discovery(self):
        (self.work / "first.md").write_text("name: sample\n\n## Sample\n\nBody.\n")
        self.build(["first.md"])
        # Run the real compiler with a spy inside its process, so caught Git
        # failures cannot hide an attempted lookup. No metadata env is set.
        runner = """
import runpy, subprocess, sys
from unittest.mock import patch, call
compiler = sys.argv.pop(1)
values = {
    ('git', 'config', 'remote.origin.url'): b'git@github.com:example/training.git',
    ('git', 'rev-parse', '--abbrev-ref', 'HEAD'): b'production',
    ('git', 'rev-parse', '--show-prefix'): b'slides/',
    ('git', 'rev-parse', '--short', 'HEAD'): b'abc123',
    ('git', 'status', '--porcelain'): b' M first.md',
}
with patch('subprocess.check_output', side_effect=lambda command, **kw: values[tuple(command)]) as spy:
    runpy.run_path(compiler, run_name='__main__')
    if __import__('os').environ['SLIDES_DEV'] == '1':
        spy.assert_not_called()
    else:
        assert spy.call_args_list == [call(list(command), stderr=subprocess.DEVNULL) for command in values]
"""
        for dev in (True, False):
            with self.subTest(dev=dev):
                env = dict(os.environ, SLIDES_DEV="1" if dev else "0")
                for key in ("REPOSITORY_URL", "BRANCH", "COMMIT"):
                    env.pop(key, None)
                result = subprocess.run(
                    [sys.executable, "-c", runner, str(SLIDES / "markmaker.py"), "deck.yml"],
                    cwd=self.work, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Could not determine", result.stderr)
                if dev:
                    self.assertIn(".debug[first.md · #sample]", result.stdout)
                    self.assertNotIn("These slides have been built from commit", result.stdout)
                else:
                    self.assertIn("https://github.com/example/training/tree/production/slides/first.md", result.stdout)
                    self.assertIn("These slides have been built from commit: abc123", result.stdout)
                    self.assertIn("M first.md", result.stdout)

    def test_dev_without_git_keeps_unrelated_warnings(self):
        self.build(["first.md"])
        env = dict(os.environ, SLIDES_DEV="1", PATH="")
        for key in ("REPOSITORY_URL", "BRANCH", "COMMIT"):
            env.pop(key, None)
        # A missing source still needs its warning; skip only Git discovery.
        manifest = yaml.safe_load((self.work / "deck.yml").read_text())
        manifest["content"].append("missing-source.md")
        (self.work / "deck.yml").write_text(yaml.safe_dump(manifest))
        result = subprocess.run([sys.executable, str(SLIDES / "markmaker.py"), "deck.yml"],
                                cwd=self.work, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Could not determine", result.stderr)
        self.assertIn("no file found: missing-source.md", result.stderr)
        self.assertIn(".debug[first.md]", result.stdout)

    def test_direct_slide_links_keep_order_slides_and_lecture_navigation(self):
        body = ("# Alpha\n\nFirst content.\n\n---\n\n"
                "name: task\nclass: exercise\ntoc: Do the task\n\n"
                "## Exercise\n\nTask content.\n\n--\n\nSecond step.\n\n---\n\n"
                "# Beta\n\nLast content.\n")
        for single in (False, True):
            for named in (False, True):
                for dev in (False, True):
                    with self.subTest(single=single, named=named, dev=dev):
                        group = {"title": "Tasks", "content": ["task.md"]} if named else ["task.md"]
                        (self.work / "task.md").write_text(body.replace("toc: Do the task\n", ""))
                        old = self.build([group], single, dev)
                        (self.work / "task.md").write_text(body)
                        new = self.build([group], single, dev)
                        links = re.findall(r"^- \[([^]]+)\]\(#([^)]+)\)$", new, re.M)
                        self.assertEqual(links, [("Table of contents", "toc" if single else "toc-section-1"),
                                                 ("Alpha", "toc-alpha"), ("Do the task", "task"), ("Beta", "toc-beta")])
                        self.assertEqual(old.count("\n---\n"), new.count("\n---\n"))
                        self.assertEqual(re.findall(r"^name: .*", old, re.M), re.findall(r"^name: .*", new, re.M))
                        self.assertEqual(re.findall(r"\[(?:Previous|Next) lecture\]\([^)]*\)", old),
                                         re.findall(r"\[(?:Previous|Next) lecture\]\([^)]*\)", new))
                        self.assertEqual(new.count("class: title"), 2)
                        self.assertEqual(new.count("class: pic"), 2)
                        self.assertIn("## Exercise", new)
                        self.assertIn("class: exercise", new)

    def test_direct_only_intro_preserves_navigation_and_toc_slide_count(self):
        for single in (False, True):
            with self.subTest(single=single):
                group = {"title": "Intro", "content": ["intro.md"]}
                (self.work / "intro.md").write_text("name: intro\n\n## Introduction\n\nContent.\n")
                old = self.build([group, ["first.md"]], single)
                (self.work / "intro.md").write_text("name: intro\ntoc: Start here\n\n## Introduction\n\nContent.\n")
                new = self.build([group, ["first.md"]], single)
                self.assertIn("- [Start here](#intro)", new)
                if not single:
                    self.assertIn("- [Start here](#intro)\n\n## ", new)
                self.assertEqual(re.findall(r"^name: .*", old, re.M), re.findall(r"^name: .*", new, re.M))
                self.assertEqual(old.count("\n---\n"), new.count("\n---\n"))
                self.assertEqual(re.findall(r"\[(?:Previous|Next|Table).*?\]\([^)]*\)", old),
                                 re.findall(r"\[(?:Previous|Next|Table).*?\]\([^)]*\)", new))
                only = self.build([["intro.md"]], single)
                self.assertIn("- [Start here](#intro)", only)
                self.assertNotIn("class: title", only)
                self.assertNotIn("class: pic", only)

    def test_excluded_slide_links_and_non_property_text_are_ignored(self):
        (self.work / "links.md").write_text(
            "class: hidden\nname: ignored\ntoc: Hidden link\n\n## Hidden\n\n--\n\nHidden step.\n\n---\n\n"
            "## Visible\n\n```\nname: code\ntoc: Code link\n```\n\n???\nname: notes\ntoc: Notes link\n")
        for single in (False, True):
            with self.subTest(single=single):
                html = self.build([["links.md", "first.md"]], single)
                self.assertNotIn("[Hidden link]", html)
                self.assertNotIn("Hidden step.", html)
                self.assertNotIn("[Code link]", html)
                self.assertNotIn("[Notes link]", html)

    def test_invalid_slide_links_fail_clearly(self):
        cases = [
            ("toc: Missing target\n\n## Slide\n", "explicit name"),
            ("name: valid\ntoc:\n\n## Slide\n", "non-empty label"),
            ("name: bad target\ntoc: Link\n\n## Slide\n", "explicit name"),
            ("name: repeated\ntoc: Link\n\n## Slide\n\n---\n\nname: repeated\n\n## Other\n", "exactly one retained slide"),
            ("name: toc-alpha\ntoc: Link\n\n## Slide\n\n---\n\n# Alpha\n\nContent.\n", "exactly one retained slide"),
            ("name: toc\ntoc: Link\n\n## Slide\n", "exactly one retained slide"),
            ("name: valid\ntoc: First\ntoc: Second\n\n## Slide\n", "Duplicate 'toc'"),
            ("name: valid\ntoc: Link\nlayout: true\n\n## Slide\n", "layout slide"),
        ]
        for content, message in cases:
            with self.subTest(message=message):
                (self.work / "bad.md").write_text(content)
                self.assertIn(message, self.build([["bad.md"]], single=True, success=False))

    def test_automatic_contents_entry_keeps_manifest_order_and_navigation(self):
        for single in (False, True):
            for placement in ("start", "middle", "end", "named"):
                with self.subTest(single=single, placement=placement):
                    if placement == "named":
                        content = [{"title": "Basics", "content": ["first.md", "toc.md", "last.md"]}]
                    else:
                        content = {"start": ["toc.md", ["first.md", "last.md"]],
                                   "middle": [["first.md"], "toc.md", ["last.md"]],
                                   "end": [["first.md", "last.md"], "toc.md"]}[placement]
                    html = self.build(content, single, prepend_toc=False)
                    links = re.findall(r"^- \[([^]]+)\]\(#([^)]+)\)$", html, re.M)
                    target = "toc" if single else "toc-section-1"
                    expected = [("Alpha", "toc-alpha"), ("Beta", "toc-beta"), ("Gamma", "toc-gamma")]
                    position = 0 if placement == "start" else 3 if placement == "end" else 2
                    expected.insert(position, ("Table of contents", target))
                    self.assertEqual(links, expected)
                    self.assertEqual(len(re.findall(r"^name: " + target + r"$", html, re.M)), 1)
                    self.assertNotIn("name: toc-table-of-contents", html)
                    self.assertEqual(html.count("class: title"), 3)
                    self.assertEqual(html.count("class: pic"), 3)
                    self.assertEqual(len(re.findall(r"^name: toc(?:-section-\d+)?$", html, re.M)),
                                     1 if single or placement != "middle" else 2)
                    self.assertIn("[Next lecture](#toc-gamma)", html)
                    self.assertIn("[Previous lecture](#toc-beta)", html)

    def test_automatic_contents_target_rejects_duplicate_anchor(self):
        for single in (False, True):
            with self.subTest(single=single):
                target = "toc" if single else "toc-section-1"
                (self.work / "collision.md").write_text("name: " + target + "\n\n## Collision\n")
                self.assertIn("exactly one retained slide", self.build([["collision.md", "first.md"]],
                              single, success=False))

    def test_reference_deck_has_toc_and_reference_slides(self):
        (self.work / "pics.md").write_text(
            "# Pictures chapter\n\n---\n\nclass: pic, reference\n\n![Network map](images/net.svg)\n\n"
            "---\n\nname: arch\nclass: pic, reference\n\n![](images/control-planes/arch.svg)\n\n"
            "---\n\nclass: pic, reference, hidden\n\n![Excluded](images/x.svg)\n\n"
            "---\n\nclass: pic\n\n![Not a reference](images/y.svg)\n\n"
            "---\n\n## Text slide\n\n```bash\n# not a chapter\n```\n")
        manifest = {"title": "Test deck", "exclude": ["hidden"],
                    "content": ["toc.md", ["first.md", "pics.md"]]}
        (self.work / "deck.yml").write_text(yaml.safe_dump(manifest, sort_keys=False))
        result = subprocess.run([sys.executable, str(SLIDES / "markmaker.py"),
                                 "--reference", "deck.reference.yml.html", "deck.yml"],
                                cwd=self.work, env=dict(os.environ, SLIDES_DEV="0"),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        # The main deck is not changed: no generated anchors.
        self.assertNotIn("name: ref-", result.stdout)
        html = (self.work / "deck.reference.yml.html").read_text()
        source = re.search(r'<textarea id="source"[^>]*>(.*)</textarea>', html, re.S).group(1)
        slides = source.split("\n---\n")
        self.assertTrue(slides[0].startswith("name: toc-section-1\n"))
        self.assertIn("**Pictures chapter**", slides[0])
        # TOC links point to slides in the same file; a slide keeps its name.
        self.assertEqual(re.findall(r"^- \[([^]]+)\]\(([^)]+)\)$", slides[0], re.M),
                         [("Network map", "#ref-1"), ("arch.svg", "#arch")])
        self.assertEqual(len(slides), 3)
        self.assertRegex(slides[1], r"^\n?name: ref-1\nclass: pic, reference\n")
        self.assertIn("name: arch\nclass: pic, reference", slides[2])
        self.assertIn("\"Test deck (reference)\"", html)
