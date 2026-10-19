"""The doctor's window. The workers run checks and fixes and report through a `post` callback;
the Tk half (below) is the only code that touches widgets, and imports tkinter lazily."""

from vs_doctor import checks, runner


def check_all(config, post):
    results = []
    for index, check in enumerate(checks.CHECKS):
        post(("checking", index, check.__name__))
        result = runner.run_check(check, config)
        post(("result", index, result))
        results.append(result)
    return results


def fix_one(index, check, result, config, post):
    post(("fixing", index))
    post(("fixed", index, runner.run_fix(result, config)))
    new_result = runner.run_check(check, config)
    post(("result", index, new_result))
    return new_result


class GuiUnavailable(Exception):
    """The window could not start, or broke part way. The caller falls back to the console."""


TITLE = "Vital Seeds Doctor"
MARK_COLOURS = {"ok": "#1a7f37", "warn": "#9a6700", "fail": "#cf222e", "skip": "#6e7781"}
DIM = "#6e7781"
POLL_MS = 100


def _build_report(results, config):
    """Feed the (muted) recording console the same lines the console flow would print."""
    from vs_doctor import report

    report.reset()
    report.header()
    for result in results:
        report.check_line(result)
    report.summary(results, config)


def run(config):
    """Open the window, run the checks, offer fixes. Returns the final results."""
    import queue
    import threading

    try:
        import sv_ttk
        import tkinter
        from tkinter import ttk

        from vs_doctor import config as doctor_config
        from vs_doctor import report

        root = tkinter.Tk()
    except Exception as error:  # noqa: BLE001 - no Tk, no sv_ttk, no display
        raise GuiUnavailable(str(error)) from error

    problems = []
    state = {"results": [], "busy": False, "checking": True, "report_path": None}
    events = queue.Queue()
    rows = []

    def on_error(exc_type, exc, tb):
        problems.append(exc)
        root.destroy()

    root.report_callback_exception = on_error
    try:
        sv_ttk.set_theme("light")
    except Exception as error:  # noqa: BLE001
        root.destroy()
        raise GuiUnavailable(str(error)) from error

    root.title(TITLE)
    root.geometry("680x560")
    root.minsize(520, 360)

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="Let's see what's poorly.", font=("", 16, "bold")).pack(anchor="w")
    status = ttk.Label(outer, text="Checking...", foreground=DIM)
    status.pack(anchor="w", pady=(0, 8))
    body = ttk.Frame(outer)
    body.pack(fill="both", expand=True)
    footer = ttk.Frame(outer)
    footer.pack(fill="x", pady=(8, 0))

    def add_row(index, name):
        frame = ttk.Frame(body, padding=(0, 4))
        frame.pack(fill="x")
        mark = ttk.Label(frame, text=" .. ", width=4)
        mark.grid(row=0, column=0, sticky="nw")
        text = ttk.Label(frame, text=name, wraplength=480, justify="left")
        text.grid(row=0, column=1, sticky="nw")
        frame.columnconfigure(1, weight=1)
        button = ttk.Button(frame, text="Fix", style="Accent.TButton", command=lambda: start_fix(index))
        rows.append({"frame": frame, "mark": mark, "text": text, "button": button, "extra": []})

    def show_result(index, result):
        row = rows[index]
        while len(state["results"]) <= index:
            state["results"].append(None)
        state["results"][index] = result
        symbol, _ = report.MARKS[result.status]
        row["mark"].configure(text=f" {symbol} ", foreground=MARK_COLOURS[result.status], font=("", 10, "bold"))
        row["text"].configure(text=result.message)
        for label in row["extra"]:
            label.destroy()
        row["extra"] = []
        for line, colour, grid_row in ((result.advice, None, 1), (result.detail, DIM, 2)):
            if line:
                label = ttk.Label(row["frame"], text=line, wraplength=480, justify="left")
                if colour:
                    label.configure(foreground=colour)
                label.grid(row=grid_row, column=1, sticky="nw")
                row["extra"].append(label)
        row["button"].grid_forget()

    def show_fix_buttons():
        for index, result in enumerate(state["results"]):
            if result and result.status == "fail" and result.fix:
                row = rows[index]
                row["button"].configure(text="Fix", state="disabled" if state["busy"] else "normal")
                row["button"].grid(row=0, column=2, sticky="ne", padx=(8, 0))

    def start_fix(index):
        if state["busy"]:
            return
        state["busy"] = True
        check = checks.CHECKS[index]
        result = state["results"][index]

        def work():
            try:
                fix_one(index, check, result, config, events.put)
                events.put(("idle",))
            except Exception as error:  # noqa: BLE001
                events.put(("error", error))

        threading.Thread(target=work, daemon=True).start()
        show_fix_buttons()

    def write_report():
        _build_report([r for r in state["results"] if r], config)
        state["report_path"] = report.save(doctor_config.report_dir(), state["report_path"])
        saved_label.configure(text=f"I've saved this report to {state['report_path']}. Send it to whoever helps you.")

    def finish_checks(results):
        state["checking"] = False
        failures = [r for r in results if r.status == "fail"]
        if failures:
            status.configure(text=f"{len(failures)} thing(s) need attention.", foreground=MARK_COLOURS["fail"])
        else:
            status.configure(text=report.random.choice(report.HAPPY_QUIPS), foreground=MARK_COLOURS["ok"])
        show_fix_buttons()
        write_report()

    def handle(event):
        kind = event[0]
        if kind == "checking":
            add_row(event[1], event[2])
        elif kind == "result":
            show_result(event[1], event[2])
        elif kind == "fixing":
            rows[event[1]]["text"].configure(text="Trying a fix...")
            rows[event[1]]["button"].configure(text="Fixing...", state="disabled")
        elif kind == "done":
            finish_checks(event[1])
        elif kind == "idle":
            state["busy"] = False
            show_fix_buttons()
            write_report()
        elif kind == "error":
            raise event[1]

    def poll():
        try:
            while True:
                handle(events.get_nowait())
        except queue.Empty:
            pass
        root.after(POLL_MS, poll)

    def checks_worker():
        try:
            events.put(("done", check_all(config, events.put)))
        except Exception as error:  # noqa: BLE001
            events.put(("error", error))

    def close():
        if state["busy"]:
            return
        if state["report_path"] is None and any(state["results"]):
            write_report()  # closed before the checks finished: still save what we have
        root.destroy()

    contact = config["doctor"]["contact"]
    docs_url = config["doctor"]["docs_url"].strip()
    ttk.Label(footer, text=f"Still stuck? {contact}", font=("", 10, "bold")).pack(anchor="w")
    if docs_url:
        ttk.Label(footer, text=f"While you wait, the Vital Seeds docs may help: {docs_url}").pack(anchor="w")
    saved_label = ttk.Label(footer, text="", foreground=DIM, wraplength=620)
    saved_label.pack(anchor="w", pady=(4, 0))
    ttk.Button(footer, text="Close", command=close).pack(anchor="e")

    root.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=checks_worker, daemon=True).start()
    root.after(POLL_MS, poll)
    try:
        root.mainloop()
    except Exception as error:  # noqa: BLE001
        raise GuiUnavailable(str(error)) from error
    if problems:
        raise GuiUnavailable(str(problems[0])) from problems[0]
    return [r for r in state["results"] if r]


def selftest() -> int:
    """Open the window and close it again, to prove Tk and the theme work. Used by CI."""
    try:
        import sv_ttk
        import tkinter

        root = tkinter.Tk()
        try:
            sv_ttk.set_theme("light")
            root.update()
        finally:
            root.destroy()
        return 0
    except Exception:  # noqa: BLE001
        return 2
