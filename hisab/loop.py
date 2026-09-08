"""Main loop: poll WhatsApp → setup or agent → reply. `--stdin` runs the same pipeline from the terminal."""
import argparse
import base64
import sys
import time
import traceback
from pathlib import Path

from . import config as cfgmod
from .agent import Agent
from .ledger import Ledger, LedgerError
from .setup import Setup
from .store import Store
from .transcribe import transcribe

HELP = "Hisab: send an entry (*2500 coffee*, a voice note, a receipt photo), a question (*month*, *balances*, *what do I owe*), *undo*, or reply to an old message with *undo*. /setup redoes setup, /clear forgets the conversation."


class Hisab:
    def __init__(self, cfg):
        self.cfg = cfg
        self.store = Store(cfg["state"]["path"], cfg["memory"]["keep_days"])
        self.ledger = Ledger(cfg["ledger"]["path"], cfg["ledger"]["currency"])
        self.setup = Setup(self.ledger, self.store)
        self.agent = Agent(cfg, self.ledger)
        self.media_dir = Path(cfg["state"]["path"]) / "media"
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def handle(self, text, msg_id=None, quoted_id=None, image=None):
        """One inbound message → (reply text, entry number or None)."""
        t = (text or "").strip()
        low = t.lower()
        if low in ("/clear", "clear", "start fresh", "new session"):
            self.store.mark_clear()
            return "Cleared.", None
        if low in ("/help", "help", "?"):
            return HELP, None
        if low == "/setup":
            return self.setup.start(), None
        if self.setup.active():
            reply, done, parked = self.setup.answer(t)
            if done and parked:
                r2, entry = self._agent(parked, None)
                return reply + "\n\n" + r2, entry
            return reply, None
        if not self.ledger.exists():
            if image or (t and not t.startswith("/")):
                q = self.setup.start(parked=t if not image else None)
                return "No ledger here yet — quick setup first, then I'll post what you sent.\n\n" + q, None
            return self.setup.start(), None
        return self._agent(t, quoted_id, image)

    def _agent(self, text, quoted_id, image=None):
        hint = self.ledger.match_rule(text) if text else None
        prefix = ""
        if quoted_id:
            rec = self.store.lookup(quoted_id)
            entry = self.store.entry_for_message(quoted_id)
            if rec:
                prefix = f"[Replying to earlier message: \"{rec.get('text','')[:300]}\"" + (f" — it posted entry #{entry}" if entry else "") + "]\n\n"
            else:
                prefix = "[Replying to an earlier message that is not on record]\n\n"
        history = self.store.window(self.cfg["memory"]["window_turns"])
        if image:
            b64 = base64.b64encode(Path(image).read_bytes()).decode()
            mime = "image/png" if str(image).endswith(".png") else "image/jpeg"
            content = [{"type": "text", "text": prefix + (text or "Receipt photo. Post it as an entry; ask one question if the amount or category is unclear.")},
                       {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]
        else:
            content = prefix + text
        try:
            reply, tools = self.agent.run(history, content, hint)
            return reply, tools.last_entry
        except LedgerError as e:
            return f"Not posted: {e}", None
        except Exception as e:  # network / model
            return f"Something failed on my side: {str(e)[:200]}", None

    # ---------- transports ----------
    def run_stdin(self):
        print("Hisab, terminal mode. Type a message; 'quit' to stop.")
        i = 0
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if line in ("quit", "exit"):
                break
            i += 1
            mid = f"stdin:{i}"
            self.store.add(mid, "in", line)
            reply, entry = self.handle(line, mid)
            self.store.add(f"stdin-out:{i}", "out", reply, entry=entry)
            if entry:
                self._mark_entry(mid, entry)
            print(reply)

    def run_whatsapp(self):
        from .wa import WhatsApp
        tok = self.cfg["secrets"]["whatsapp_token"]
        if not tok:
            sys.exit("WHATSAPP_TOKEN is empty; put it in .env")
        wa = WhatsApp(tok, self.cfg["whatsapp"]["poll_timeout"], self.cfg["whatsapp"]["chunk_chars"])
        offset = self.store.offset()
        print(f"Polling WhatsApp. Ledger: {self.ledger.dir}")
        while True:
            try:
                msgs, nxt = wa.poll(offset)
            except Exception as e:
                print(f"poll failed: {e}; retrying in 5s", file=sys.stderr)
                time.sleep(5)
                continue
            for m in msgs:
                # idempotent by WhatsApp message id: a replayed batch (crash, restart, backlog drain) never posts twice
                if m.get("id") and self.store.lookup(m["id"]):
                    continue
                try:
                    self._handle_wa(wa, m)
                except Exception:
                    traceback.print_exc()
            # offset advances only after the batch is handled, so a crash mid-batch replays rather than drops
            if nxt and nxt != offset:
                offset = nxt
                self.store.set_offset(offset)

    def _handle_wa(self, wa, m):
        frm, typ, mid = m.get("from"), m.get("type"), m.get("id")
        quoted = (m.get("context") or {}).get("id")
        self.store.set_creator(frm)
        wa.typing(mid)
        text, image = None, None
        if typ == "text":
            text = m["text"]["body"]
        elif typ == "audio":
            path, _ = wa.download(m["audio"]["id"], self.media_dir)
            if not path:
                wa.send(frm, "Couldn't fetch that voice note."); return
            try:
                text = transcribe(path, self.cfg["secrets"]["openrouter_key"], self.cfg["transcription"]["model"], self.cfg["transcription"]["language"])
            except Exception as e:
                wa.send(frm, f"Couldn't transcribe that voice note ({str(e)[:120]}). Send it as text."); return
            text = f"[Voice note]: {text}"
        elif typ == "image":
            path, _ = wa.download(m["image"]["id"], self.media_dir)
            if not path:
                wa.send(frm, "Couldn't fetch that image."); return
            image = path
            text = (m["image"].get("caption") or "").strip()
        else:
            wa.send(frm, f"Can't read {typ} yet — text, voice notes and photos only."); return
        self.store.add(mid, "in", text or "[image]")
        reply, entry = self.handle(text, mid, quoted, image)
        ids = wa.send(frm, reply)
        for i in ids:
            self.store.add(i, "out", reply, entry=entry)
        if entry:
            self._mark_entry(mid, entry)

    def _mark_entry(self, mid, entry):
        # re-record the inbound with its entry so a later quoted reply resolves to the number
        self.store.add(mid, "note", "", entry=entry)


def main():
    ap = argparse.ArgumentParser(prog="hisab")
    ap.add_argument("--config", default=None)
    ap.add_argument("--stdin", action="store_true", help="terminal mode, no WhatsApp")
    a = ap.parse_args()
    cfgmod.load_dotenv()
    cfg = cfgmod.load(a.config)
    app = Hisab(cfg)
    if a.stdin:
        app.run_stdin()
    else:
        app.run_whatsapp()


if __name__ == "__main__":
    main()
