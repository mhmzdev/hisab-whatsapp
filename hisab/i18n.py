"""Fixed strings in the three reply languages. The model's own replies follow the language line in the system prompt."""
import re

LANGS = ("en", "ur", "roman")

S = {
 "greeting": {
  "en": "Welcome to Hisab · حساب میں خوش آمدید\nWhich language? Reply *English*, *اردو* or *Roman Urdu*.",
  "ur": None, "roman": None},
 "no_ledger_parked": {
  "en": "No ledger here yet — quick setup first, then I'll post what you sent.",
  "ur": "ابھی کوئی کھاتہ نہیں — پہلے مختصر سیٹ اپ، پھر آپ کا پیغام درج کروں گا۔",
  "roman": "Abhi koi khata nahi — pehle chhota sa setup, phir aap ka message post karunga."},
 "no_ledger": {
  "en": "No ledger here yet — quick setup first.",
  "ur": "ابھی کوئی کھاتہ نہیں — پہلے مختصر سیٹ اپ۔",
  "roman": "Abhi koi khata nahi — pehle chhota sa setup."},
 "cleared": {"en": "Cleared.", "ur": "صاف کر دیا۔", "roman": "Clear kar diya."},
 "help": {
  "en": "Hisab: send an entry (*2500 coffee*, a voice note, a receipt photo), a question (*month*, *balances*, *what do I owe*), *undo*, or reply to an old message with *undo*. /setup redoes setup, /lang changes language, /clear forgets the conversation, *export-ledger* sends a ZIP backup.",
  "ur": "حساب: اندراج بھیجیں (*2500 chai*، وائس نوٹ، رسید کی تصویر)، سوال پوچھیں (*mahina*، *balance*، *kitna dena hai*)، *undo* لکھیں، یا پرانے پیغام پر ریپلائی کر کے *undo*۔ /setup سیٹ اپ دوبارہ، /lang زبان، /clear گفتگو بھول جاؤ، *export-ledger* سے ZIP بیک اپ۔",
  "roman": "Hisab: entry bhejein (*2500 chai*, voice note, receipt ki photo), sawal poochein (*mahina*, *balance*, *kitna dena hai*), *undo* likhein, ya purane message par reply kar ke *undo*. /setup dobara setup, /lang zabaan, /clear guftagu bhool jao, *export-ledger* se ZIP backup."},
 "lang_set": {"en": "Language: English.", "ur": "زبان: اردو۔", "roman": "Zabaan: Roman Urdu."},
 "lang_ask": {"en": "Reply *English*, *اردو* or *Roman Urdu*.", "ur": "*English*، *اردو* یا *Roman Urdu* لکھیں۔", "roman": "*English*, *اردو* ya *Roman Urdu* likhein."},
 "voice_fail": {
  "en": "Couldn't transcribe that voice note ({err}). Send it as text.",
  "ur": "وائس نوٹ سمجھ نہیں آیا ({err})۔ لکھ کر بھیجیں۔",
  "roman": "Voice note samajh nahi aaya ({err}). Likh kar bhejein."},
 "fetch_fail": {"en": "Couldn't fetch that.", "ur": "یہ فائل نہیں مل سکی۔", "roman": "Yeh file nahi mil saki."},
 "unsupported": {
  "en": "Can't read {typ} yet — text, voice notes and photos only.",
  "ur": "{typ} ابھی نہیں پڑھ سکتا — صرف ٹیکسٹ، وائس نوٹ اور تصویر۔",
  "roman": "{typ} abhi nahi parh sakta — sirf text, voice note aur photo."},
 "not_posted": {"en": "Not posted: {err}", "ur": "درج نہیں ہوا: {err}", "roman": "Post nahi hua: {err}"},
 "failed": {"en": "Something failed on my side: {err}", "ur": "میری طرف سے مسئلہ ہوا: {err}", "roman": "Meri taraf se masla hua: {err}"},
 "too_many": {"en": "Too many steps for one message; try a shorter one.", "ur": "ایک پیغام کے لیے بہت زیادہ مراحل؛ چھوٹا پیغام بھیجیں۔", "roman": "Ek message ke liye bohat zyada steps; chhota message bhejein."},
 "export_ready": {
  "en": "Here's your ledger — the canonical markdown files, nothing else.",
  "ur": "یہ آپ کا کھاتہ ہے — صرف اصل مارک ڈاؤن فائلیں، کچھ اور نہیں۔",
  "roman": "Yeh raha aap ka khata — sirf asal markdown files, aur kuch nahi."},
 "export_too_large": {
  "en": "Ledger export is {mb} MB, over WhatsApp's 16 MB document limit.",
  "ur": "کھاتے کی فائل {mb} MB ہے، WhatsApp کی 16 MB حد سے زیادہ۔",
  "roman": "Khata file {mb} MB hai, WhatsApp ki 16 MB limit se zyada."},
 "export_fail": {"en": "Couldn't send the ledger export ({err}). Try again in a bit.",
  "ur": "کھاتہ بھیجا نہیں جا سکا ({err})۔ تھوڑی دیر میں دوبارہ کوشش کریں۔",
  "roman": "Khata bheja nahi ja saka ({err}). Thodi dair mein dobara koshish karein."},
 "quota_warning": {
  "en": "Heads up: {used}/{limit} replies used this month.",
  "ur": "دھیان رہے: اس مہینے {used}/{limit} جوابات استعمال ہو چکے ہیں۔",
  "roman": "Dhyan rahe: is mahine {used}/{limit} replies istemal ho chuke hain."},
 "quota_exceeded": {
  "en": "Monthly limit of {limit} AI replies reached — resumes next month. /help, /lang and export-ledger still work.",
  "ur": "اس مہینے کی {limit} AI جوابات کی حد پوری ہو گئی — اگلے مہینے دوبارہ شروع ہوگی۔ /help، /lang اور export-ledger اب بھی کام کریں گے۔",
  "roman": "Is mahine ki {limit} AI replies ki limit poori ho gayi — agle mahine dobara shuru hogi. /help, /lang aur export-ledger ab bhi kaam karenge."},
}

Q = {
 "mode": {"en": "Is this ledger *personal* or for a *shop*?",
          "ur": "یہ کھاتہ *ذاتی* ہے یا *دکان* کا؟",
          "roman": "Yeh khata *personal* hai ya *shop* ka?"},
 "currency": {"en": "Currency? (reply PKR, USD, …)", "ur": "کرنسی؟ (PKR, USD, …)", "roman": "Currency? (PKR, USD, …)"},
 "money": {"en": "Your money accounts, comma-separated, first one is the default. e.g. *Alfalah bank, cash, Easypaisa wallet*",
           "ur": "آپ کے پیسوں کے اکاؤنٹس، کوما سے الگ، پہلا ڈیفالٹ ہوگا۔ مثلاً *Alfalah bank, cash, Easypaisa wallet*",
           "roman": "Aap ke paison ke accounts, comma se alag, pehla default hoga. Maslan *Alfalah bank, cash, Easypaisa wallet*"},
 "cards": {"en": "Any credit cards? Name and statement day, e.g. *Alfalah 15*. Or *none*.",
           "ur": "کوئی کریڈٹ کارڈ؟ نام اور اسٹیٹمنٹ کا دن، مثلاً *Alfalah 15*۔ یا *nahi*۔",
           "roman": "Koi credit card? Naam aur statement day, maslan *Alfalah 15*. Ya *nahi*."},
 "income": {"en": "Where does money come in? e.g. *salary, freelance*. Or *none*.",
            "ur": "پیسے کہاں سے آتے ہیں؟ مثلاً *salary, freelance*۔ یا *nahi*۔",
            "roman": "Paise kahan se aate hain? Maslan *salary, freelance*. Ya *nahi*."},
 "income_shop": {"en": "Besides sales, any other income? e.g. *commission*. Or *none*.",
                 "ur": "سیل کے علاوہ کوئی اور آمدنی؟ مثلاً *commission*۔ یا *nahi*۔",
                 "roman": "Sale ke ilawa koi aur aamdani? Maslan *commission*. Ya *nahi*."},
 "investments": {"en": "Do you want to track investments? Names, e.g. *Meezan fund, plot*. Or *no*.",
                 "ur": "سرمایہ کاری ٹریک کرنی ہے؟ نام لکھیں، مثلاً *Meezan fund, plot*۔ یا *nahi*۔",
                 "roman": "Investments track karni hain? Naam likhein, maslan *Meezan fund, plot*. Ya *nahi*."},
 "donations": {"en": "Track donations as a category? *yes* or *no*.",
               "ur": "عطیات الگ کیٹیگری میں؟ *haan* یا *nahi*۔",
               "roman": "Donations alag category mein? *haan* ya *nahi*."},
 "suppliers": {"en": "Suppliers the shop buys from, comma-separated, e.g. *Metro, Ali traders*. Or *none*.",
               "ur": "دکان جن سے مال خریدتی ہے، کوما سے الگ، مثلاً *Metro, Ali traders*۔ یا *nahi*۔",
               "roman": "Suppliers jin se maal aata hai, comma se alag, maslan *Metro, Ali traders*. Ya *nahi*."},
 "staff": {"en": "Staff names, for advances and salaries, e.g. *Bilal, Ahmed*. Or *none*.",
           "ur": "ملازمین کے نام، ایڈوانس اور تنخواہ کے لیے، مثلاً *Bilal, Ahmed*۔ یا *nahi*۔",
           "roman": "Staff ke naam, advance aur tankhwah ke liye, maslan *Bilal, Ahmed*. Ya *nahi*."},
 "fixed": {"en": "Monthly fixed costs for the budget: rent and salaries, e.g. *rent 40000, salaries 60000*. Or *skip*.",
           "ur": "ماہانہ مقررہ اخراجات بجٹ کے لیے: کرایہ اور تنخواہیں، مثلاً *rent 40000, salaries 60000*۔ یا *skip*۔",
           "roman": "Mahana fixed kharche budget ke liye: kiraya aur tankhwah, maslan *rent 40000, salaries 60000*. Ya *skip*."},
 "done": {"en": "Setup done. The ledger is at {dir}/. Send an entry any time, e.g. *2500 coffee*, a voice note, or a receipt photo. *balance <account> <amount>* sets a starting balance.",
          "ur": "سیٹ اپ مکمل۔ کھاتہ {dir}/ میں ہے۔ کبھی بھی اندراج بھیجیں، مثلاً *2500 chai*، وائس نوٹ، یا رسید کی تصویر۔ *balance <account> <amount>* سے ابتدائی بیلنس سیٹ ہوتا ہے۔",
          "roman": "Setup mukammal. Khata {dir}/ mein hai. Kabhi bhi entry bhejein, maslan *2500 chai*, voice note, ya receipt ki photo. *balance <account> <amount>* se shuru ka balance set hota hai."},
 "done_parked": {"en": " Now posting what you sent first.", "ur": " اب آپ کا پہلا پیغام درج کر رہا ہوں۔", "roman": " Ab aap ka pehla message post kar raha hoon."},
 "mode_again": {"en": "Reply *personal* or *shop*.", "ur": "*ذاتی* یا *دکان* لکھیں۔", "roman": "*personal* ya *shop* likhein."},
 "currency_again": {"en": "Reply with a currency code, e.g. *PKR*.", "ur": "کرنسی کوڈ لکھیں، مثلاً *PKR*۔", "roman": "Currency code likhein, maslan *PKR*."},
}

MODEL_LANG = {
 "en": "Reply in English.",
 "ur": "Reply in Urdu script (اردو). Keep numbers as digits and account names exactly as declared (Latin). Shapes: after posting «درج #12 — چائے 300 — مہینے کا خرچ 48,200»; after undo «ہٹا دیا #12 — چائے»; questions in Urdu.",
 "roman": "Reply in Roman Urdu — Urdu in Latin letters the way people type on WhatsApp. Keep numbers as digits and account names as declared. Shapes: after posting «post ho gaya #12 — chai 300 — mahine ka kharch 48,200»; after undo «hata diya #12 — chai»; questions in Roman Urdu.",
}


def s(key, lang, **kw):
    d = S[key]
    txt = d.get(lang) or d["en"]
    return txt.format(**kw) if kw else txt


def q(key, lang, **kw):
    d = Q[key]
    txt = d.get(lang) or d["en"]
    return txt.format(**kw) if kw else txt


def parse_lang(text):
    t = (text or "").strip().lower()
    if re.search(r"roman|rom\b|3", t):
        return "roman"
    if re.search(r"اردو|urdu|ur\b|2", t):
        return "ur"
    if re.search(r"english|eng|en\b|angrezi|1", t):
        return "en"
    return None
