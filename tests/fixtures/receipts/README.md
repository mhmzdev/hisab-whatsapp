# Receipt fixtures

Real receipt screenshots, partly blurred, for `python3 tests/check_receipts.py`: the by-hand check that the model reads the direction of a transfer receipt (#43). It needs a model key, is never part of the repo check (`tests/smoke.py`), and skips a case cleanly, exit 0, while its image is missing.

The script runs setup with the holder name `Muhammad Hamza` (`--holder` changes it). Each image goes through the agent against a fresh temp ledger with Alfalah bank, Easypaisa wallet and cash declared, and the check asserts tool calls, never wording.

| Case | Image | What it shows | Passes when |
|---|---|---|---|
| `r1` | `r1.jpg` | Easypaisa: "Sent to" a company, "Sent by MUHAMMAD HAMZA" | an entry moves money **out** of a money account, or the question's candidates are all money-out |
| `r2` | `r2.jpg` | Easypaisa: "Sent to" a private person, "Sent by MUHAMMAD HAMZA" | the same; a question also offers `assets:receivable:<name>` |
| `r3` | `r3.jpg` | Easypaisa app view: "Successfully Sent to Waleed Hamza Flutter", no sender named. The recipient shares a word with the holder | money **out**, no `income:` posting, no money-in question: the whole name must not match, and "Sent to" decides |
| `r4` | `r4.jpg` | ABL via Raast: "Transferred To: MUHAMMAD HAMZA", "From Account: ALI SHAKEEL" | money **in**, never an expense: a "Transferred To" label is not a direction word, the holder is the receiver |
| `r1-stranger` | `r1.jpg` again | the same receipt, with the holder set to `Ayesha Khan` (`--stranger`) | a question about direction, and **no** entry: the holder is on neither side |

`.png` works too. A missing image skips its case.

## Adding or replacing an image

Keep the party names and the amount readable, or the model has no sides to read. Blur account numbers, phone numbers, IBANs, reference and transaction ids, QR codes. Review each image before committing it: these files are public.
