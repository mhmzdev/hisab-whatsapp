"""Fixed strings in the two languages Hisab is written in, English and Urdu. Users may also chat in Roman Urdu:
the model answers that in kind (MODEL_LANG["en"]), but no fixed string is ever written in it."""
import re

LANGS = ("en", "ur")

S = {
 # sent before any language is known, so one bilingual text; the answer sets the language (setup.py)
 "greeting": {
  "en": "Welcome to Hisab · حساب میں خوش آمدید\nIs this ledger *personal* or for a *shop*?\nیہ کھاتہ *ذاتی* ہے یا *دکان* کا؟",
  "ur": None},
 "lang_note": {
  "en": "_Replying in English. Send /lang اردو to switch._",
  "ur": "_جواب اردو میں۔ انگلش کے لیے /lang english بھیجیں۔_"},
 "no_ledger_parked": {
  "en": "No ledger here yet — quick setup first, then I'll post what you sent.",
  "ur": "ابھی کوئی کھاتہ نہیں — پہلے مختصر سیٹ اپ، پھر آپ کا پیغام درج کروں گا۔"},
 "no_ledger": {
  "en": "No ledger here yet — quick setup first.",
  "ur": "ابھی کوئی کھاتہ نہیں — پہلے مختصر سیٹ اپ۔"},
 "cleared": {"en": "Cleared.", "ur": "صاف کر دیا۔"},
 "help": {
  "en": "Hisab: send an entry (*2500 coffee*, a voice note, a receipt photo), a question (*month*, *balances*, *what do I owe*), *undo*, or reply to an old message with *undo*. /setup redoes setup, /lang changes language, /clear forgets the conversation, *export-ledger* sends a ZIP backup.",
  "ur": "حساب: اندراج بھیجیں (*2500 chai*، وائس نوٹ، رسید کی تصویر)، سوال پوچھیں (*mahina*، *balance*، *kitna dena hai*)، *undo* لکھیں، یا پرانے پیغام پر ریپلائی کر کے *undo*۔ /setup سیٹ اپ دوبارہ، /lang زبان، /clear گفتگو بھول جاؤ، *export-ledger* سے ZIP بیک اپ۔"},
 "lang_set": {"en": "Language: English.", "ur": "زبان: اردو۔"},
 "lang_ask": {"en": "Send */lang English* or */lang اردو*.", "ur": "*/lang English* یا */lang اردو* بھیجیں۔"},
 "voice_fail": {
  "en": "Couldn't transcribe that voice note ({err}). Send it as text.",
  "ur": "وائس نوٹ سمجھ نہیں آیا ({err})۔ لکھ کر بھیجیں۔"},
 "fetch_fail": {"en": "Couldn't fetch that.", "ur": "یہ فائل نہیں مل سکی۔"},
 "unsupported": {
  "en": "Can't read {typ} yet — text, voice notes and photos only.",
  "ur": "{typ} ابھی نہیں پڑھ سکتا — صرف ٹیکسٹ، وائس نوٹ اور تصویر۔"},
 "not_posted": {"en": "Not posted: {err}", "ur": "درج نہیں ہوا: {err}"},
 "failed": {"en": "Something failed on my side: {err}", "ur": "میری طرف سے مسئلہ ہوا: {err}"},
 "too_many": {"en": "Too many steps for one message; try a shorter one.", "ur": "ایک پیغام کے لیے بہت زیادہ مراحل؛ چھوٹا پیغام بھیجیں۔"},
 "export_ready": {
  "en": "Here's your ledger — the canonical markdown files, nothing else.",
  "ur": "یہ آپ کا کھاتہ ہے — صرف اصل مارک ڈاؤن فائلیں، کچھ اور نہیں۔"},
 "export_too_large": {
  "en": "Ledger export is {mb} MB, over WhatsApp's 16 MB document limit.",
  "ur": "کھاتے کی فائل {mb} MB ہے، WhatsApp کی 16 MB حد سے زیادہ۔"},
 "export_fail": {"en": "Couldn't send the ledger export ({err}). Try again in a bit.",
  "ur": "کھاتہ بھیجا نہیں جا سکا ({err})۔ تھوڑی دیر میں دوبارہ کوشش کریں۔"},
 "quota_warning": {
  "en": "Heads up: {used}/{limit} replies used this month.",
  "ur": "دھیان رہے: اس مہینے {used}/{limit} جوابات استعمال ہو چکے ہیں۔"},
 # Hosted mode (#7). Both are sent before the user's language is known, so each is the same
 # bilingual text under both keys: English and Urdu on their own lines.
 "pending_reminder": {
  "en": "Hisab · حساب\nNot connected yet. Send the code shown in the portal, e.g. *verify 482913*\nابھی جڑا نہیں۔ پورٹل میں دکھایا گیا کوڈ بھیجیں، مثلاً *verify 482913*",
  "ur": "Hisab · حساب\nNot connected yet. Send the code shown in the portal, e.g. *verify 482913*\nابھی جڑا نہیں۔ پورٹل میں دکھایا گیا کوڈ بھیجیں، مثلاً *verify 482913*"},
 "welcome": {
  "en": "Connected ✓ · جڑ گیا ✓\nThis agent is now your Hisab.\nیہ ایجنٹ اب آپ کا حساب ہے۔",
  "ur": "Connected ✓ · جڑ گیا ✓\nThis agent is now your Hisab.\nیہ ایجنٹ اب آپ کا حساب ہے۔"},
 "quota_exceeded": {
  "en": "Monthly limit of {limit} AI replies reached — resumes next month. /help, /lang and export-ledger still work.",
  "ur": "اس مہینے کی {limit} AI جوابات کی حد پوری ہو گئی — اگلے مہینے دوبارہ شروع ہوگی۔ /help، /lang اور export-ledger اب بھی کام کریں گے۔"},
}

Q = {
 "mode": {"en": "Is this ledger *personal* or for a *shop*?",
          "ur": "یہ کھاتہ *ذاتی* ہے یا *دکان* کا؟"},
 "currency": {"en": "Currency? (reply PKR, USD, …)", "ur": "کرنسی؟ (PKR, USD, …)"},
 "money": {"en": "Your money accounts, comma-separated, first one is the default. e.g. *Alfalah bank, cash, Easypaisa wallet*",
           "ur": "آپ کے پیسوں کے اکاؤنٹس، کوما سے الگ، پہلا ڈیفالٹ ہوگا۔ مثلاً *Alfalah bank, cash, Easypaisa wallet*"},
 "cards": {"en": "Any credit cards? Name and statement day, e.g. *Alfalah 15*. Or *none*.",
           "ur": "کوئی کریڈٹ کارڈ؟ نام اور اسٹیٹمنٹ کا دن، مثلاً *Alfalah 15*۔ یا *nahi*۔"},
 "income": {"en": "Where does money come in? e.g. *salary, freelance*. Or *none*.",
            "ur": "پیسے کہاں سے آتے ہیں؟ مثلاً *salary, freelance*۔ یا *nahi*۔"},
 "income_shop": {"en": "Besides sales, any other income? e.g. *commission*. Or *none*.",
                 "ur": "سیل کے علاوہ کوئی اور آمدنی؟ مثلاً *commission*۔ یا *nahi*۔"},
 "investments": {"en": "Do you want to track investments? Names, e.g. *Meezan fund, plot*. Or *no*.",
                 "ur": "سرمایہ کاری ٹریک کرنی ہے؟ نام لکھیں، مثلاً *Meezan fund, plot*۔ یا *nahi*۔"},
 "donations": {"en": "Track donations as a category? *yes* or *no*.",
               "ur": "عطیات الگ کیٹیگری میں؟ *haan* یا *nahi*۔"},
 "suppliers": {"en": "Suppliers the shop buys from, comma-separated, e.g. *Metro, Ali traders*. Or *none*.",
               "ur": "دکان جن سے مال خریدتی ہے، کوما سے الگ، مثلاً *Metro, Ali traders*۔ یا *nahi*۔"},
 "staff": {"en": "Staff names, for advances and salaries, e.g. *Bilal, Ahmed*. Or *none*.",
           "ur": "ملازمین کے نام، ایڈوانس اور تنخواہ کے لیے، مثلاً *Bilal, Ahmed*۔ یا *nahi*۔"},
 "fixed": {"en": "Monthly fixed costs for the budget: rent and salaries, e.g. *rent 40000, salaries 60000*. Or *skip*.",
           "ur": "ماہانہ مقررہ اخراجات بجٹ کے لیے: کرایہ اور تنخواہیں، مثلاً *rent 40000, salaries 60000*۔ یا *skip*۔"},
 "done": {"en": "Setup done. The ledger is at {dir}/. Send an entry any time, e.g. *2500 coffee*, a voice note, or a receipt photo. *balance <account> <amount>* sets a starting balance.",
          "ur": "سیٹ اپ مکمل۔ کھاتہ {dir}/ میں ہے۔ کبھی بھی اندراج بھیجیں، مثلاً *2500 chai*، وائس نوٹ، یا رسید کی تصویر۔ *balance <account> <amount>* سے ابتدائی بیلنس سیٹ ہوتا ہے۔"},
 "done_parked": {"en": " Now posting what you sent first.", "ur": " اب آپ کا پہلا پیغام درج کر رہا ہوں۔"},
 "mode_again": {"en": "Reply *personal* or *shop*.", "ur": "*ذاتی* یا *دکان* لکھیں۔"},
 "currency_again": {"en": "Reply with a currency code, e.g. *PKR*.", "ur": "کرنسی کوڈ لکھیں، مثلاً *PKR*۔"},
}

MODEL_LANG = {
 "en": "Reply in English. If the user writes Roman Urdu (Urdu in Latin letters, the way people type on WhatsApp), reply in Roman Urdu instead, same shapes: after posting «post ho gaya #12 — chai 300 — mahine ka kharch 48,200»; after undo «hata diya #12 — chai». Keep numbers as digits and account names as declared.",
 "ur": "Reply in Urdu script (اردو). Keep numbers as digits and account names exactly as declared (Latin). Shapes: after posting «درج #12 — چائے 300 — مہینے کا خرچ 48,200»; after undo «ہٹا دیا #12 — چائے»; questions in Urdu.",
}


def s(key, lang, **kw):
    d = S[key]
    txt = d.get(lang) or d["en"]
    return txt.format(**kw) if kw else txt


def q(key, lang, **kw):
    d = Q[key]
    txt = d.get(lang) or d["en"]
    return txt.format(**kw) if kw else txt


def norm_lang(code):
    """A stored language outside LANGS (an old "roman" setting) reads as English."""
    return code if code in LANGS else "en"


def detect_lang(text):
    """The language of a first answer: any Urdu-script letter means Urdu, anything else English."""
    return "ur" if re.search(r"[\u0600-\u06FF]", text or "") else "en"


def parse_lang(text):
    t = (text or "").strip().lower()
    if "roman" in t:
        return None  # not a language Hisab is written in; "roman urdu" must not read as Urdu
    if re.search(r"اردو|urdu|ur\b|2", t):
        return "ur"
    if re.search(r"english|eng|en\b|angrezi|1", t):
        return "en"
    return None
