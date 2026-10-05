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

    def build(self, content, single=False, dev=False, success=True):
        manifest = {"title": "Test deck", "content": ["toc.md"] + content,
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
                self.assertEqual(links, ["Alpha", "Beta", "Gamma"])
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
                        self.assertEqual(links, [("Alpha", "toc-alpha"), ("Do the task", "task"), ("Beta", "toc-beta")])
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
