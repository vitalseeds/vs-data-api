"""Everything the user sees: the art, a line per check, the summary, and the saved report."""

import datetime
import random
from textwrap import indent

from rich.console import Console
from rich.text import Text

# record=True keeps a copy of everything printed, for save()
console = Console(record=True, safe_box=True, emoji=False, highlight=False)

SEEDLING = r"""
      _
    _(_)_      vsdata-doctor
   (_)@(_)     Let's see what's poorly.
     (_)\
        |
   ~~~~~~~~~
"""

WILTED = r"""
        ,
     __/
    (__  )~
       \|
   ~~~~~~~~~
"""

HAPPY_QUIPS = [
    "Everything is growing nicely.",
    "Clean bill of health. Back to the seeds!",
    "Nothing wrong here. Have a biscuit.",
]

SAD_QUIPS = [
    "Don't worry, it's not the seeds' fault.",
    "Every gardener has a bad day.",
    "We'll have this blooming again soon.",
]

MARKS = {"ok": ("OK", "green"), "warn": ("!!", "yellow"), "fail": ("XX", "red"), "skip": ("--", "dim")}


def header():
    console.print(Text(SEEDLING, style="green"))


def check_line(result):
    mark, style = MARKS[result.status]
    console.print(Text.assemble((f" {mark} ", f"bold {style}"), " ", result.message))
    if result.detail:
        console.print(Text(indent(result.detail, "      "), style="dim"))


def ask_fix() -> bool:
    answer = console.input(Text("      Shall I try? [y/N] "))
    return answer.strip().lower() in ("y", "yes")


def fix_outcome(worked: bool):
    if worked:
        console.print(Text("      That worked.", style="green"))
    else:
        console.print(Text("      That didn't work, sorry.", style="red"))


def summary(results, config):
    failures = [result for result in results if result.status == "fail"]
    console.print()
    if not failures:
        console.print(Text(random.choice(HAPPY_QUIPS), style="bold green"))
        return
    console.print(Text(WILTED, style="yellow"))
    console.print(Text("What to do:", style="bold"))
    for number, result in enumerate(failures, start=1):
        console.print(Text(f"  {number}. {result.message} {result.advice}".rstrip()))
    console.print()
    console.print(Text(f"Still stuck? {config['doctor']['contact']}", style="bold"))
    docs_url = config["doctor"]["docs_url"].strip()
    if docs_url:
        console.print(Text(f"While you wait, the Vital Seeds docs may help: {docs_url}"))
    console.print(Text(random.choice(SAD_QUIPS), style="italic"))


def save(folder):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"doctor-{datetime.datetime.now():%Y-%m-%d-%H%M%S}.txt"
    console.save_text(str(path), clear=False)
    return path


def saved(path):
    console.print(Text(f"\nI've saved this report to {path}. Send it to whoever helps you.", style="dim"))


def pause():
    console.input(Text("\nPress Enter to close."))
