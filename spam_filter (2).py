"""

=============================================================

Inteligentný Spam Filter s Naivným Bayesom a Učením zo Chýb

=============================================================

"""

import os

import json

import sqlite3

import pickle

import re

import logging

from datetime import datetime

from typing import Tuple, Dict, Any, Optional

import numpy as np

from sklearn.naive_bayes import MultinomialNB

from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.model_selection import train_test_split

from sklearn.metrics import accuracy_score, classification_report

from sklearn.pipeline import Pipeline

logging.basicConfig(

level=logging.INFO,

format="%(asctime)s [%(levelname)s] %(message)s",

handlers=[logging.StreamHandler()]

)

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "spam_filter.db")

MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

# ─────────────────────────────────────────────────────────────────────────────

# DATABÁZA

# ─────────────────────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    c.executescript("""

        CREATE TABLE IF NOT EXISTS emails (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            text TEXT NOT NULL,

            label INTEGER NOT NULL,

            source TEXT DEFAULT 'dataset',

            created TEXT DEFAULT (datetime('now'))

        );

        CREATE TABLE IF NOT EXISTS corrections (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            email_text TEXT NOT NULL,

            predicted INTEGER NOT NULL,

            correct_label INTEGER NOT NULL,

            created TEXT DEFAULT (datetime('now'))

        );

        CREATE TABLE IF NOT EXISTS stats (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            total_emails INTEGER DEFAULT 0,

            spam_count INTEGER DEFAULT 0,

            ham_count INTEGER DEFAULT 0,

            corrections INTEGER DEFAULT 0,

            model_accuracy REAL DEFAULT 0.0,

            last_trained TEXT DEFAULT (datetime('now'))

        );

        INSERT OR IGNORE INTO stats (id) VALUES (1);

    """)

    conn.commit()

    return conn

def save_email(conn, text, label, source="user"):

    conn.execute("INSERT INTO emails (text, label, source) VALUES (?, ?, ?)", (text, label, source))

    conn.commit()

def save_correction(conn, text, predicted, correct):

    conn.execute("INSERT INTO corrections (email_text, predicted, correct_label) VALUES (?, ?, ?)", (text, predicted, correct))

    save_email(conn, text, correct, source="correction")

    conn.execute("UPDATE stats SET corrections = corrections + 1 WHERE id = 1")

    conn.commit()

def update_stats(conn, accuracy, total, spam, ham):

    conn.execute(

        "UPDATE stats SET total_emails=?, spam_count=?, ham_count=?, model_accuracy=?, last_trained=datetime('now') WHERE id=1",

        (total, spam, ham, accuracy)

    )

    conn.commit()

def get_stats(conn) -> Dict[str, Any]:

    row = conn.execute("SELECT * FROM stats WHERE id = 1").fetchone()

    corrections = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]

    if row:

        return {

            "total_emails" : row[1],

            "spam_count"   : row[2],

            "ham_count"    : row[3],

            "corrections"  : corrections,

            "model_accuracy": round(row[5] * 100, 2),

            "last_trained" : row[6],

        }

    return {}

def load_all_emails(conn):

    rows = conn.execute("SELECT text, label FROM emails").fetchall()

    return [r[0] for r in rows], [r[1] for r in rows]

# ─────────────────────────────────────────────────────────────────────────────

# NLP PREDSPRACOVANIE

# ─────────────────────────────────────────────────────────────────────────────

STOP_WORDS = {

    "a","aby","aj","ak","ako","ale","alebo","ani","až","bez","by","byť",

    "cez","či","ďalší","do","ešte","ho","ich","im","je","jeho","jej","ju",

    "k","každý","kde","keď","ktorý","lebo","len","ma","mám","mi","môcť",

    "môj","my","na","nad","nám","nie","no","o","od","on","ona","oni","ono",

    "our","po","pod","podľa","pokiaľ","pre","pred","pri","sa","sú","si",

    "so","som","svôj","s","tak","taktiež","tam","ten","teda","tiež","to",

    "toho","tu","už","v","vám","váš","veľmi","vo","všetci","vy","z","za",

    "zo","že","this","the","and","for","are","was","with","have","from",

    "that","will","your","you","not","but","they","his","her","been",

    "more","also","can","has","had","its","our","out","who","than","then",

    "so","if","or","an","at","be","by","do","in","is","it","no","of",

    "on","to","up","us","we","me","my","he","she","we","as","at","by",

}

def preprocess(text: str) -> str:

    text = text.lower()

    text = re.sub(r'http\S+|www\S+', ' url ', text)

    text = re.sub(r'\S+@\S+', ' email ', text)

    text = re.sub(r'\d+[.,]?\d*\s*(eur|usd|gbp|€|\$|%)', ' money ', text)

    text = re.sub(r'\d+', ' num ', text)

    text = re.sub(r'!{2,}', ' vykricnik ', text)

    text = re.sub(r'\?{2,}', ' otaznik ', text)

    text = re.sub(r'[^a-záäčďéíľĺňóôŕšťúýžA-ZÁÄČĎÉÍĽĹŇÓÔŔŠŤÚÝŽ\s]', ' ', text)

    tokens = text.split()

    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]

    return " ".join(tokens)

# ─────────────────────────────────────────────────────────────────────────────

# MODEL

# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline() -> Pipeline:

    return Pipeline([

        ("tfidf", TfidfVectorizer(

            preprocessor=preprocess,

            ngram_range=(1, 3),

            max_features=30000,

            sublinear_tf=True,

            min_df=1,

        )),

        ("clf", MultinomialNB(alpha=0.05))

    ])

def train_model(texts, labels) -> Tuple[Pipeline, float, str]:

    if len(texts) < 10:

        raise ValueError("Príliš málo dát na tréning (min. 10 e-mailov).")

    X_train, X_test, y_train, y_test = train_test_split(

        texts, labels, test_size=0.2, random_state=42, stratify=labels

    )

    pipeline = build_pipeline()

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)

    report = classification_report(y_test, y_pred, target_names=["Ham", "Spam"], zero_division=0)

    log.info("Tréning dokončený. Presnosť: %.2f%%", accuracy * 100)

    return pipeline, accuracy, report

def save_model(pipeline):

    with open(MODEL_PATH, "wb") as f:

        pickle.dump(pipeline, f)

    log.info("Model uložený: %s", MODEL_PATH)

def load_model():

    if os.path.exists(MODEL_PATH):

        with open(MODEL_PATH, "rb") as f:

            return pickle.load(f)

    return None

def predict(pipeline, text: str) -> Tuple[str, float]:

    proba = pipeline.predict_proba([text])[0]

    pred = pipeline.predict([text])[0]

    label = "spam" if pred == 1 else "ham"

    return label, float(proba[pred])

# ─────────────────────────────────────────────────────────────────────────────

# DATASET  (500 príkladov)

# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_EMAILS = [

    # ── ANGLICKÝ SPAM ─────────────────────────────────────────────────────────

    ("Congratulations! You've won $1,000,000! Click here to claim your prize now!", 1),

    ("FREE money! Make $5000 per week working from home. No experience needed!", 1),

    ("URGENT: Your account has been suspended. Verify your identity immediately.", 1),

    ("Buy cheap Viagra online! Best prices guaranteed. Click here!", 1),

    ("You have been selected for a special offer. Act now before it expires!", 1),

    ("Earn money fast! Work from home opportunity. Limited time offer!", 1),

    ("Your PayPal account is at risk! Login now to secure your account.", 1),

    ("Nigerian prince needs your help transferring millions. Huge reward guaranteed!", 1),

    ("Win a free iPhone 15! You are our lucky winner! Claim now!", 1),

    ("Hot singles in your area! Meet them tonight! Free registration!", 1),

    ("LOSE WEIGHT FAST! Amazing diet pill. Results guaranteed or money back!", 1),

    ("Make $10,000 per month with our proven system. No skills required!", 1),

    ("Your email won the lottery! Claim your $500,000 prize today!", 1),

    ("Special discount on medications. Buy online without prescription!", 1),

    ("FINAL NOTICE: Your invoice is overdue. Pay immediately to avoid legal action!", 1),

    ("Cheap diploma! Get your college degree online. No classes needed!", 1),

    ("Incredible investment opportunity! 500% return guaranteed!", 1),

    ("Your credit card has been charged. Dispute now or lose money!", 1),

    ("FREE adult content! Click here for unlimited access!", 1),

    ("Casino bonus! $1000 free chips! Play now and win big!", 1),

    ("Limited offer: Get rich quick with crypto! Invest $100 get $10,000!", 1),

    ("You qualify for a loan! Bad credit OK! Apply now!", 1),

    ("Exclusive deal just for you! 90% off everything! Today only!", 1),

    ("Alert: Suspicious login detected. Verify your account now!", 1),

    ("Double your income! Secret method revealed. Click to learn more!", 1),

    ("WINNER! You have been chosen to receive a $500 Walmart gift card!", 1),

    ("Earn $500 daily from your phone! No investment needed!", 1),

    ("Your computer has a virus! Call our support number immediately!", 1),

    ("FREE Netflix subscription for 1 year! Limited offer. Sign up now!", 1),

    ("Bankruptcy lawyers hate this trick! Erase your debt in 30 days!", 1),

    ("You are pre-approved for a $50,000 loan. No credit check required!", 1),

    ("Act now! Your subscription expires today. Renew to keep your benefits!", 1),

    ("Millions of singles want to meet you! Join free today!", 1),

    ("Claim your free gift card worth $1000. Survey takes 2 minutes!", 1),

    ("WARNING: Your computer is infected with 5 viruses. Click to fix now!", 1),

    ("Make passive income while you sleep! Our AI does all the work!", 1),

    ("Invest in gold now! Prices will triple in 6 months guaranteed!", 1),

    ("Your Amazon account has been locked. Click here to restore access!", 1),

    ("IRS NOTICE: You owe back taxes. Pay now to avoid arrest!", 1),

    ("Buy followers and likes! 10,000 Instagram followers for $9.99!", 1),

    ("Miracle weight loss supplement! Lose 20 pounds in 2 weeks!", 1),

    ("You have unclaimed insurance money! Act fast before it expires!", 1),

    ("Grow your business with our secret marketing formula! $0 ad spend!", 1),

    ("BREAKING: Stock tip that will make you rich overnight! Buy now!", 1),

    ("Unlock your full potential with this ancient money ritual!", 1),

    ("Get a black card with no spending limit! Apply today!", 1),

    ("Work from home typing jobs! $25 per hour. No experience needed!", 1),

    ("Your social security number has been compromised. Call immediately!", 1),

    ("Congratulations, you are today's millionth visitor! Collect prize!", 1),

    ("Exclusive VIP invitation: Make $3000 this weekend. Limited spots!", 1),

    ("Debt collectors can't touch you with this one legal loophole!", 1),

    ("FREE business class flight upgrade! Click to confirm your seat!", 1),

    ("This diet pill is banned in 12 countries because it works too well!", 1),

    ("Make $500 today just by sharing this link with your friends!", 1),

    ("Your email address has been selected for a cash prize. Verify now!", 1),

    ("Buy real human hair wigs at 80% off! Offer ends midnight!", 1),

    ("Guaranteed approval credit card! Zero interest for 24 months!", 1),

    ("Your online order needs verification. Confirm details or order cancelled!", 1),

    ("Last chance: Claim your free vacation package before it expires!", 1),

    ("Meet rich sugar daddies in your area tonight! Signup is free!", 1),

    # ── ANGLICKÝ HAM ──────────────────────────────────────────────────────────

    ("Hi John, can we schedule a meeting for tomorrow at 3pm to discuss the project?", 0),

    ("Please find attached the quarterly report. Let me know if you have questions.", 0),

    ("Your Amazon order #123-456 has been shipped. Expected delivery: Friday.", 0),

    ("Reminder: Team standup meeting is at 9am tomorrow. Please be on time.", 0),

    ("Thank you for your application. We will review it and get back to you.", 0),

    ("Hi, just wanted to check in and see how you're doing. Hope all is well!", 0),

    ("The project deadline has been moved to next week. Please update your schedule.", 0),

    ("Can you please review the attached document and provide feedback?", 0),

    ("Your appointment with Dr. Smith is confirmed for Monday at 2pm.", 0),

    ("Meeting notes from yesterday's discussion are attached. Please review.", 0),

    ("Could you help me understand this error in the code? I'm stuck on this issue.", 0),

    ("Happy birthday! Hope you have a wonderful day with friends and family.", 0),

    ("The server maintenance is scheduled for Sunday 2am-4am. Plan accordingly.", 0),

    ("Your subscription has been renewed. Thank you for being a valued customer.", 0),

    ("Please submit your timesheet by end of day Friday for payroll processing.", 0),

    ("I wanted to follow up on our conversation from last week about the proposal.", 0),

    ("The library book you reserved is now available for pickup. Valid for 3 days.", 0),

    ("Your flight booking is confirmed. Check-in opens 24 hours before departure.", 0),

    ("Team lunch is tomorrow at noon at the Italian restaurant on Main Street.", 0),

    ("Please remember to complete the mandatory security training by month end.", 0),

    ("I've reviewed your code and left some comments. Great work overall!", 0),

    ("Your package was delivered to the mailroom. Please pick it up today.", 0),

    ("Can we reschedule our call to Thursday? I have a conflict on Wednesday.", 0),

    ("The new software update is available. Please install it at your convenience.", 0),

    ("Thank you for attending the workshop. Please fill out the feedback form.", 0),

    ("The budget proposal has been approved. We can proceed with the project.", 0),

    ("Reminder: Please submit your expense reports by the 15th of this month.", 0),

    ("Your parking permit has been renewed for the next quarter.", 0),

    ("The conference call is scheduled for 2pm EST. Dial-in details attached.", 0),

    ("We are pleased to offer you the position of Senior Developer. Details attached.", 0),

    ("Your direct deposit of $2,450 has been processed and will be available Friday.", 0),

    ("Please review and sign the attached NDA before our meeting next week.", 0),

    ("The office will be closed on Monday for the public holiday.", 0),

    ("Your child's parent-teacher conference is scheduled for November 15th at 4pm.", 0),

    ("The grocery delivery is scheduled between 2-4pm today. Please be available.", 0),

    ("Your dental cleaning appointment is confirmed for December 3rd at 10am.", 0),

    ("The IT team will be upgrading the VPN software on all laptops this weekend.", 0),

    ("Please join us for the company all-hands meeting on Friday at 3pm.", 0),

    ("Your gym membership renewal is due next month. No action needed if continuing.", 0),

    ("The book club meeting is this Thursday at 7pm. We are discussing chapter 8-12.", 0),

    ("Here is the updated roadmap for Q3. Please review and share any concerns.", 0),

    ("Your pull request has been reviewed. Two minor changes requested.", 0),

    ("We received your return request and will process it within 3 business days.", 0),

    ("The weekly newsletter is attached. Feel free to forward to colleagues.", 0),

    ("I'll be out of office from Dec 20 to Jan 3. Contact Sarah for urgent matters.", 0),

    ("Your insurance claim has been received and is under review.", 0),

    ("Reminder: Annual performance reviews start next Monday. Please prepare.", 0),

    ("Could you send me the files from last quarter's audit? Thanks!", 0),

    ("The venue for the conference has been changed to the Grand Hotel downtown.", 0),

    ("We appreciate your feedback and will implement the suggested improvements.", 0),

    ("Your two-factor authentication has been successfully enabled.", 0),

    ("Please confirm you received the contract we sent earlier this week.", 0),

    ("The training session on data privacy is mandatory for all staff.", 0),

    ("Just a heads up that the printer on the 3rd floor is out of toner.", 0),

    ("Your application for remote work has been approved starting next month.", 0),

    ("The sprint review is on Friday at 4pm. Please have your demos ready.", 0),

    ("Congrats on the promotion! Well deserved. Looking forward to working together.", 0),

    ("The client approved the design mockups. We can proceed to development.", 0),

    ("Your tax documents for 2023 are ready to download from the portal.", 0),

    ("We've updated our privacy policy. Please read the changes at your convenience.", 0),

    # ── SLOVENSKÝ SPAM ────────────────────────────────────────────────────────

    ("Gratulujeme! Vyhrali ste 500 000 EUR! Kliknite sem a získajte svoju výhru!", 1),

    ("Ste víťazom našej lotérie! Vaša cena čaká. Kontaktujte nás ihneď!", 1),

    ("VÝHRA! Váš e-mail bol vyžrebovaný. Získajte 100 000 EUR ešte dnes!", 1),

    ("Blahoželáme! Vyhrali ste luxusné auto. Potvrďte svoju adresu teraz!", 1),

    ("Ste naším šťastným výhercom týždňa! Cena: 250 000 EUR. Konajte hneď!", 1),

    ("Vaše telefónne číslo vyhralo hlavnú cenu v lotérii. Zavolajte nám!", 1),

    ("ŠPECIÁLNA VÝHRA: iPhone 15 Pro zadarmo! Len pre vás. Kliknite tu!", 1),

    ("Získajte svoju výhru 1 000 000 EUR. Stačí kliknúť a potvrdiť totožnosť!", 1),

    ("Vyhrali ste dovolenku na Maledivách! Rezervujte si miesto ešte dnes!", 1),

    ("Lotéria EuroMillions: Váš lístok vyhral! Nárokujte si výhru do 48 hodín!", 1),

    ("Zarobte 5000 EUR týždenne z pohodlia domova! Bez skúseností. Začnite hneď!", 1),

    ("Tajná metóda zarábania online. 10 000 EUR mesačne garantovaných!", 1),

    ("Investujte 100 EUR a získajte 10 000 EUR za mesiac. 100% istota!", 1),

    ("Kryptomena BOOM! Investujte teraz a zdvojnásobte peniaze za 24 hodín!", 1),

    ("Exkluzívna investičná príležitosť. Návratnosť 500%. Obmedzený počet miest!", 1),

    ("Rýchla pôžička bez dokladovania príjmu! Schválenie do 10 minút!", 1),

    ("Máte dlhy? Pomôžeme vám! Pôžička 50 000 EUR bez záruky. Volajte teraz!", 1),

    ("Zarobte na forexe bez skúseností! Náš robot zarába za vás 24/7!", 1),

    ("Binárne opcie: Zarobte 1000 EUR denne. Registrujte sa zadarmo!", 1),

    ("Nigérijský princ potrebuje vašu pomoc. Odmena 10% z 5 miliónov USD!", 1),

    ("URGENT: Váš bankový účet bol zablokovaný. Prihláste sa ihneď!", 1),

    ("Upozornenie: Podozrivá aktivita na vašom účte. Overte totožnosť teraz!", 1),

    ("Váš PayPal účet bude zrušený. Kliknite sem na overenie do 24 hodín!", 1),

    ("Slovenská sporiteľňa: Váš účet bol kompromitovaný. Konajte okamžite!", 1),

    ("VÚB Banka: Neautorizovaná transakcia 899 EUR. Potvrďte alebo zrušte!", 1),

    ("Tatra banka: Váš internetbanking bol zablokovaný. Obnovte prístup tu!", 1),

    ("Apple ID: Váš účet bol použitý v cudzej krajine. Zabezpečte ho hneď!", 1),

    ("Google: Niekto sa prihlásil do vášho účtu z Číny. Zmeňte heslo ihneď!", 1),

    ("Facebook: Váš profil bude vymazaný. Potvrdením predídete zrušeniu!", 1),

    ("DHL: Váš balík čaká. Zaplaťte poplatok 2,99 EUR za doručenie.", 1),

    ("Slovenská pošta: Balík zadržaný na colnici. Uhraďte 4,50 EUR online.", 1),

    ("Finančná správa SR: Máte nedoplatok dane. Zaplaťte do 48 hodín!", 1),

    ("Polícia SR: Bol zaznamenaný pokus o podvod z vášho počítača. Konajte!", 1),

    ("Microsoft: Váš počítač má vírus. Zavolajte technickú podporu ihneď!", 1),

    ("Schudnite 10 kg za 2 týždne! Zázračná tabletka. Bez diéty a cvičenia!", 1),

    ("Viagra a Cialis online bez predpisu! Diskrétne doručenie domov!", 1),

    ("Prírodný liek na cukrovku. Lekári nechcú, aby ste to vedeli!", 1),

    ("Zázračný krém na vrásky. Vyzerajte o 20 rokov mladšie za týždeň!", 1),

    ("Kasíno bonus 1000 EUR zadarmo! Registrujte sa a hrajte bez rizika!", 1),

    ("Online poker: Získajte 500 EUR bonus pre nových hráčov!", 1),

    ("Stávkujte na futbal a zarobte! 100 EUR bonus pre nových hráčov!", 1),

    ("Získajte diplom VŠ za 3 mesiace! Uznávaný certifikát. Bez skúšok!", 1),

    ("Slobodné ženy vo vašom meste čakajú na vás! Registrujte sa zadarmo!", 1),

    ("Horúce rande dnes večer! Tisíce žien hľadajú partnera vo vašom okolí!", 1),

    ("Dospelý obsah ZADARMO! Kliknite pre neobmedzený prístup!", 1),

    ("Ray-Ban okuliare 90% ZĽAVA! Len dnes. Objednajte za 9,99 EUR!", 1),

    ("Originálne hodinky Rolex za 99 EUR! Limitovaná ponuka. Kúpte teraz!", 1),

    ("Lacné letenky do Dubaja za 19 EUR! Len dnes. Rezervujte ihneď!", 1),

    ("Solárne panely ZADARMO! Štátna dotácia 100%. Požiadajte teraz!", 1),

    ("Predplatné zrušené. Vrátime vám 89 EUR. Zadajte číslo karty!", 1),

    ("Vaša objednávka Amazon nie je možné doručiť. Aktualizujte adresu tu!", 1),

    ("FLASH SALE 95% ZĽAVA! Len nasledujúcich 10 minút. Kúpte teraz!", 1),

    ("Reklamná výhra: Ste 1 000 000. zákazník! Cena čaká. Kliknite!", 1),

    ("Práca v zahraničí: UK, Nemecko, Rakúsko. Plat 3000 EUR. Nástup ihneď!", 1),

    ("Hľadáme kuriérov na prepravu balíkov. Zárobky 200 EUR denne!", 1),

    ("Modelka/model hľadaná. Platba 500 EUR za deň. Foto/video. Volajte!", 1),

    ("Prepisovanie textov doma. 3 EUR za stranu. Neobmedzené množstvo!", 1),

    ("Klikajte na reklamy a zarábajte. 0,50 EUR za klik. Neobmedzene!", 1),

    ("Pomôžte chorým deťom! Darujte 1 EUR a zachránite život!", 1),

    ("SOS! Rodina stratila všetko pri požiari. Prispejte cez tento účet!", 1),

    ("Pyramídová hra ZAKONNÁ v SR! Zarobte tisíce EUR za pár dní!", 1),

    ("Zbavte sa dlhov legálne! Osobný bankrot v 3 krokoch. Poradíme!", 1),

    ("Váš e-mail bude zmazaný pre nečinnosť. Prihláste sa a aktivujte ho!", 1),

    ("Zadarmo VPN na neobmedzený čas! Skryte svoju aktivitu online!", 1),

    ("Netflix Premium zdarma na 1 rok! Špeciálna akcia. Registrujte sa!", 1),

    ("Váš iPhone bol hacknutý! Stiahnite ochranu ihneď zadarmo!", 1),

    ("Sociálna poisťovňa: Máte nárok na vrátenie 450 EUR. Požiadajte tu!", 1),

    ("Ministerstvo financií: Daňový preplatok 320 EUR. Žiadajte vrátenie!", 1),

    ("Jasnovidka Mária vidí vašu budúcnosť. Prvá konzultácia ZADARMO!", 1),

    ("Zázračná voda lieči všetko! Vedci šokovaní. Objednajte 3+1 zadarmo!", 1),

    ("Ochrana osobných údajov GDPR. Zaplaťte 29 EUR alebo pokuta!", 1),

    ("Refinancujte hypotéku a ušetrite 200 EUR mesačne! Volajte zadarmo!", 1),

    ("Energie lacnejšie o 40%! Premeňte si dodávateľa. Volajte ihneď!", 1),

    ("Lekárska štúdia hľadá dobrovoľníkov. Zárobok 500 EUR za víkend!", 1),

    ("Anaboliká a steroidy online. Rýchly svalový rast. Diskrétne!", 1),

    ("Predajte nám vaše zlato za najlepšiu cenu! Hotovosť ihneď!", 1),

    ("Váš účet bol napadnutý! Zmeňte heslo kliknutím na tento odkaz ihneď!", 1),

    ("Zarobte na kryptomenách bez skúseností! Náš AI robot robí všetko!", 1),

    ("Lekári nenávidia tento trik! Schudnite 15 kg za 10 dní bez námahy!", 1),

    ("Gratulujem! Ste 1 000 000. návštevník stránky. Vyberte si cenu!", 1),

    ("Exkluzívna ponuka! Zlatá kreditná karta bez poplatkov navždy!", 1),

    ("Orange: Vaše číslo bude prenesené. Zastavte prenos kliknutím tu!", 1),

    ("Telekom: Nezaplatený účet 89 EUR. Zaplaťte do zajtra alebo odpojenie!", 1),

    ("Vaša doména expiruje zajtra. Obnovte ihneď alebo stratíte web!", 1),

    ("Doma si vyrábajte výrobky a predávajte ich nám! Zárobky 1500 EUR!", 1),

    ("Online recenzie a hodnotenia. 5 EUR za recenziu. Tisíce produktov!", 1),

    ("Predám byt 3-izbový Bratislava 60 000 EUR! Naliehavý predaj. Volajte!", 1),

    ("Investícia do nehnuteľností v Dubaji. Výnos 15% ročne. Informujte sa!", 1),

    ("Adoptujte zviera na diaľku za 2 EUR mesačne! Certifikát dostanete!", 1),

    ("Tajné stretnutia pre ženatých. 100% diskrétnosť zaručená!", 1),

    ("Výherná kombinácia čísel pre loto tento týždeň! Kúpte tajomstvo!", 1),

    ("Zbierka pre vojnových utečencov. 100% ide priamo ľuďom v núdzi!", 1),

    ("Doručovateľ: Balík vrátený kvôli chýbajúcim colným poplatkom 6 EUR!", 1),

    ("GLS: Váš balík čaká na vyzdvihnutie. Potvrďte doručovacie okno!", 1),

    ("Klimatizácia za 499 EUR komplet s montážou! Obmedzená ponuka!", 1),

    ("Alarm pre dom za 1 EUR mesačne! Profesionálna ochrana. Kliknite!", 1),

    ("Cestovné poistenie na rok za 19 EUR! Celá Európa. Objednajte teraz!", 1),

    ("Zarábajte písaním článkov online! 50 EUR za článok. Bez skúseností!", 1),

    ("UPOZORNENIE: Your account was accessed from unknown location! Verify now!", 1),

    ("Výhra! You won our weekly lottery prize of 10 000 EUR! Claim here!", 1),

    ("ZADARMO: Get your free iPhone 15 today! Len pre prvých 100 ľudí!", 1),

    ("Zarábajte online working from home! No experience needed. Start today!", 1),

    # ── NOVÝ SLOVENSKÝ SPAM ───────────────────────────────────────────────────

    ("Vaša kreditná karta bola kompromitovaná. Okamžite zablokujte kartu tu!", 1),

    ("POZOR: Zistili sme neobvyklú aktivitu na vašom účte. Potvrďte identitu!", 1),

    ("Získajte štátnu dotáciu 5000 EUR na zateplenie domu. Požiadajte dnes!", 1),

    ("Len dnes: Notebook za 99 EUR! Výpredaj skladu. Objednajte okamžite!", 1),

    ("Váš email vyhral v súťaži 50 000 EUR. Kontaktujte nás do 24 hodín!", 1),

    ("Pracujte pre Google z domu! Plat 3000 EUR mesačne. Registrujte sa!", 1),

    ("Detský tábor ZADARMO! Dotovaný štátom. Prihláste dieťa do piatku!", 1),

    ("Nový zákon: Každý občan SR má nárok na príspevok 800 EUR. Žiadajte!", 1),

    ("Pohybujte sa a zarábajte! Aplikácia platí 1 EUR za každý kilometer!", 1),

    ("Vaša SIM karta bude zablokovaná. Overte totožnosť kliknutím tu!", 1),

    ("VÍRUS DETECTED na vašom zariadení! Stiahnite ochranu zadarmo ihneď!", 1),

    ("Ponúkame vám prácu správcu sociálnych sietí. 2500 EUR home office!", 1),

    ("Zaregistrujte firmu v Dubaji za 500 EUR. Nulové dane. Informujte sa!", 1),

    ("Váš Instagram bol hacknutý! Obnovte prístup kliknutím na tento link!", 1),

    ("Špeciálna akcia Lidl: Nakupte za 50 EUR a získajte tablet zadarmo!", 1),

    ("Tesco vernostná karta: Máte 5000 bodov na vyzdvihnutie. Aktivujte!", 1),

    ("Mobilná aplikácia platí 5 EUR za každú recenziu. Sťahujte zadarmo!", 1),

    ("Prvý mesiac streaming TV zadarmo! Potom len 1 EUR mesačne. Skúste!", 1),

    ("Váš router bol napadnutý. Zmeňte heslo podľa návodu na tomto linku!", 1),

    ("Kúpte bitcoiny teraz! Cena stúpne 10x do konca roka. Zaručene!", 1),

    ("Rýchla online pôžička 5000 EUR. Schválenie za 5 minút. Bez ručiteľa!", 1),

    ("Právna pomoc s dlhmi ZADARMO! Zbavíme vás dlhov do 6 mesiacov!", 1),

    ("Váš trestný register bude zverejnený. Zaplaťte 29 EUR na odstránenie!", 1),

    ("Exkluzívny webinár: Zarobte milión za rok. Registrácia zadarmo!", 1),

    ("Doručenie balíka zlyhalo. Uhraďte 1,99 EUR a naplánujte nové doručenie!", 1),

    ("Upozornenie Alza: Váš účet bol zablokovaný pre podozrivú aktivitu!", 1),

    ("Najlacnejšie poistenie auta v SR! Ušetrite až 400 EUR ročne. Kalkulujte!", 1),

    ("Posielajte SMS a zarábajte 0,30 EUR za každú. Neobmedzený zárobok!", 1),

    ("Tajná diéta celebrít. Schudnite 8 kg za týždeň bez námahy!", 1),

    ("Vaše fotky sú verejné na internete! Stiahnite ich kliknutím sem!", 1),

    ("Výpredaj sezóny! Všetko za 1 EUR! Len dnes. Objednajte teraz!", 1),

    ("Váš počítač odosiela vaše heslá hackerom. Stiahnite ochranu zadarmo!", 1),

    ("Správa DPD: Balík nedoručený. Zaplaťte 3 EUR poplatok za uskladnenie!", 1),

    ("Rodinné poistenie od 2 EUR mesačne! Celá rodina chránená. Uzavrite!", 1),

    ("Predám auto BMW 2019 za 8000 EUR. Naliehavý predaj. Volajte ihneď!", 1),

    ("Americká víza zaručene! Vybavíme za 2 týždne. Kontaktujte nás!", 1),

    ("Vaša objednávka bola zrušená. Vrátime peniaze zadaním čísla karty!", 1),

    ("Tajný spôsob chudnutia z TV! Schudnite 20 kg za mesiac zaručene!", 1),

    ("Bezplatná konzultácia s odborníkom na investície. Zarobte viac!", 1),

    ("Urgentná ponuka bytu! 2-izbový Bratislava centrum 55 000 EUR!", 1),

    # ── ĎALŠÍ NOVÝ ANGLICKÝ SPAM ─────────────────────────────────────────────

    ("CLAIM NOW: You have a pending wire transfer of $85,000 awaiting approval!", 1),

    ("Doctors don't want you to know this one weird trick for perfect health!", 1),

    ("Your Microsoft account will be deleted in 24 hours unless you act now!", 1),

    ("Earn unlimited Bitcoin daily! Our trading bot has a 97% success rate!", 1),

    ("EXCLUSIVE: Join our VIP club and earn $2,000 weekly from home!", 1),

    ("Weight loss secret BANNED by big pharma! Lose 30 lbs guaranteed!", 1),

    ("You have inherited $4.5 million from a distant relative. Contact us!", 1),

    ("FREE iPhone 16 for completing our 30-second survey! Limited stock!", 1),

    ("Your email ID has won £850,000 in the UK National Lottery. Claim today!", 1),

    ("Reverse type 2 diabetes in 28 days with this ancient herb secret!", 1),

    ("URGENT RECALL: Your car has a dangerous defect. Schedule repair now!", 1),

    ("Get unlimited free gift cards! 100% legal and verified. Join now!", 1),

    ("Your Netflix payment failed. Update billing info to keep watching!", 1),

    ("Join 50,000 members making $300/day trading options from their phones!", 1),

    ("FINAL WARNING: Unresolved debt on your account. Pay or face lawsuit!", 1),

    ("Make $1,000 per day copy-pasting links. No experience needed!", 1),

    ("Exclusive: Donald Trump's secret investment that made him billions!", 1),

    ("Grow your hair back in 30 days! Doctors are shocked by this discovery!", 1),

    ("Your account shows suspicious activity. Secure it now or lose access!", 1),

    ("FREE $750 Cash App payment! Verify your account to receive funds!", 1),

    # ── ĎALŠÍ NOVÝ SLOVENSKÝ HAM ─────────────────────────────────────────────

    ("Ahoj, môžeme sa stretnúť zajtra o 10:00 na porade ohľadom projektu?", 0),

    ("V prílohe nájdete kvartálnu správu. Dajte vedieť ak máte otázky.", 0),

    ("Posielam zápisnicu z dnešného stretnutia. Prosím skontrolujte.", 0),

    ("Termín odovzdania projektu je presunutý na piatok 17:00.", 0),

    ("Potrebujem od vás podklady do stredy. Môžete mi ich poslať?", 0),

    ("Dobrý deň, potvrdzujem prijatie vašej objednávky č. 2024-1547.", 0),

    ("Prosím o schválenie faktúry č. 2024-089 do konca týždňa.", 0),

    ("Organizujem tímový obed v piatok. Môžete prísť o 12:00?", 0),

    ("Posielam aktualizovaný harmonogram projektu. Prosím skontrolujte.", 0),

    ("Máte čas na krátky hovor dnes popoludní ohľadom zmluvy?", 0),

    ("Pripomínam pracovnú poradu v utorok o 9:00 v zasadačke A.", 0),

    ("Váš návrh zmluvy bol prijatý. Podpísaná verzia v prílohe.", 0),

    ("Oznamujem, že od 1.4. budem na materskej dovolenke.", 0),

    ("Vyplňte prosím dochádzku za minulý mesiac do zajtra.", 0),

    ("Stretnutie s klientom Novák sa presúva na štvrtok o 14:00.", 0),

    ("Vaša objednávka č. SK-2024-8847 bola úspešne prijatá.", 0),

    ("Balík bol odoslaný. Sledovacie číslo: SK123456789. Doručenie zajtra.", 0),

    ("Váš tovar bol doručený do výdajného miesta Packeta v Košiciach.", 0),

    ("Reklamácia č. 2024-123 bola prijatá. Vybavenie do 30 dní.", 0),

    ("Potvrdzujeme vrátenie platby 89 EUR na vašu kartu do 5 dní.", 0),

    ("Výpis z účtu za mesiac február bol vygenerovaný. Dostupný v appke.", 0),

    ("Trvalý príkaz na nájomné 450 EUR bol úspešne vykonaný.", 0),

    ("Vaša žiadosť o hypotéku bola postúpená na schválenie. Čakajte 5 dní.", 0),

    ("Mesačný výpis z kreditnej karty: Obrat 342,50 EUR. Splatnosť 15.3.", 0),

    ("Termín k lekárovi MUDr. Kováč je potvrdený na stredu 14:00.", 0),

    ("Výsledky krvných testov sú dostupné v systéme eZdravie.", 0),

    ("Pripomíname preventívnu prehliadku. Objednajte sa na tel. 02/1234567.", 0),

    ("Ambulancia bude zatvorená 24-25. decembra. Pohotovosť: 02/9876543.", 0),

    ("Žiadosť o rodný list bola vybavená. Dokument si vyzdvihnite na matrike.", 0),

    ("Daňové priznanie za rok 2023 bolo prijaté. Preplatok: 180 EUR.", 0),

    ("Sociálna poisťovňa: Výška dôchodku od 1.1.2024 je 580 EUR mesačne.", 0),

    ("Úrad práce: Vaša žiadosť o dávku v nezamestnanosti bola schválená.", 0),

    ("Rezervácia letu OK-1234 Bratislava-Londýn 15.6. je potvrdená.", 0),

    ("Hotel Panorama Vysoké Tatry: Check-in 22.7. o 15:00. Tešíme sa!", 0),

    ("Filmové lístky na film v sobotu o 20:15 v kine Lumière potvrdené.", 0),

    ("Aktualizácia systému prebehne v noci z piatku na sobotu 2:00-4:00.", 0),

    ("Váš GitHub Pull Request bol schválený a zlúčený do main vetvy.", 0),

    ("Správa bytového domu: Výmena výťahu prebehne 15.-17. marca.", 0),

    ("Schôdza vlastníkov bytov sa koná v stredu o 18:00 vo vchode č. 3.", 0),

    ("Upozornenie: Prerušenie dodávky teplej vody 20.3. od 8:00 do 16:00.", 0),

    ("Ahoj Miro, kedy si free na kávu? Rád by som sa stretol.", 0),

    ("Ďakujem za krásny darček k narodeninám! Veľmi ma potešil.", 0),

    ("Pôjdeme cez víkend na výlet do Tatier? Počasie vyzerá skvelo!", 0),

    ("Všetko najlepšie k narodeninám! Prajem ti veľa zdravia a šťastia.", 0),

    ("Plánujem oslavu 30-tín. Môžeš prísť v sobotu o 18:00?", 0),

    ("Vážený študent, skúškové obdobie začína 10. januára. Sledujte rozvrh.", 0),

    ("Vaša záverečná práca bola prijatá na hodnotenie. Obhajoba 15.6.", 0),

    ("Stipendijná komisia rozhodla o pridelení štipendia vo výške 200 EUR.", 0),

    ("Školský výlet do Viedne je plánovaný na 15. marca. Poplatok 45 EUR.", 0),

    ("Rodičovské združenie sa koná v pondelok o 17:00 v triede 5.B.", 0),

    ("Mamina, nezabudni zajtra zobrať Petra z tréningu o 17:30.", 0),

    ("Objednala som servis auta na piatok o 9:00. Môžeš ísť?", 0),

    ("Elektrikár príde v stredu medzi 10:00-12:00. Prosím buď doma.", 0),

    ("Plánujeme Vianoce u babičky. Môžete prísť 24.12. na obed o 12:00?", 0),

    ("Detský lekár: Petko má kontrolu v piatok o 8:30. Nezabudnite očkovací.", 0),

    ("Vaša žiadosť o prácu na pozíciu Softvérový inžinier bola prijatá.", 0),

    ("Pozývame vás na pracovný pohovor v stredu o 10:00 na naše sídlo.", 0),

    ("Pracovná ponuka: Účtovník, plat 1800 EUR, Bratislava, nástup dohodou.", 0),

    ("Hodnotenie zamestnanca na rok 2023: Výborné. Odmena 500 EUR.", 0),

    ("Newsletter: Nové pravidlá ochrany osobných údajov platné od 1.5.2024.", 0),

    ("Potvrdzujeme zmenu hesla k vášmu účtu. Ak ste to neboli vy, kontaktujte nás.", 0),

    ("Dvojfaktorové overenie bolo úspešne aktivované na vašom účte.", 0),

    ("Vaše predplatné Netflix sa obnoví 15. marca. Suma: 15,99 EUR.", 0),

    ("Dobrý deň, prosím o cenovú ponuku na opravu strechy rodinného domu.", 0),

    ("Ďakujem za rýchle vybavenie objednávky. Produkt dorazil v poriadku.", 0),

    ("Oznamujem absenciu dňa 15.3. z dôvodu návštevy lekára.", 0),

    ("Môžete mi prosím poslať faktúru za minulý mesiac? Potrebujem ju do účtovníctva.", 0),

    ("Dovolenka bola schválená. Čerpanie: 10.-20. júla. Príjemný odpočinok!", 0),

    ("Prosím o potvrdenie účasti na školení bezpečnosti práce v utorok.", 0),

    ("Informujeme vás o zmene otvárací hodín pobočky od 1. apríla.", 0),

    ("Váš príspevok do diskusie bol schválený moderátorom. Ďakujeme!", 0),

    ("Zasielame potvrdenie o návšteve múzea pre školskú skupinu 25 žiakov.", 0),

    ("Knižnica: Kniha ktorú ste si rezervovali je pripravená na vyzdvihnutie.", 0),

    ("Vaša recenzia produktu pomohla iným zákazníkom. Ďakujeme za hodnotenie!", 0),

    ("Pripomíname termín platby nájomného do 5. dňa v mesiaci.", 0),

    ("Zápisnica zo stretnutia rodičov je zverejnená na webe školy.", 0),

    ("Veterinárna klinika: Očkovanie vášho psa je naplánované na 5. mája.", 0),

    ("Poistenie domu bolo úspešne uzatvorené. Zmluva v prílohe.", 0),

    ("Váš nový bankový účet bol úspešne otvorený. Číslo účtu v prílohe.", 0),

    ("Technická kontrola vozidla prebehla úspešne. Platnosť do 15.6.2026.", 0),

    ("Zasielame výsledky prijímacieho konania na strednú školu.", 0),

    ("Prosím odpovedzte na tento email či vám vyhovuje navrhnutý termín.", 0),

    ("Tréning futbalového tímu sa presúva zo stredy na štvrtok o 17:00.", 0),

    ("Vaša žiadosť o parkovacie miesto bola zaradená do poradia. Čakajte.", 0),

    ("Obec informuje o výrube stromov na ulici Hlavná v dňoch 20.-22.3.", 0),

    ("Zasielame vám zoznam požadovaných dokumentov k žiadosti o úver.", 0),

    ("Súťaž vo varení sa koná v sobotu o 10:00 v kultúrnom dome. Príďte!", 0),

    ("Informujeme vás že oprava výťahu bola dokončená. Je opäť v prevádzke.", 0),

    ("Nová trasa autobusu číslo 42 platí od 1. apríla. Cestovný poriadok v prílohe.", 0),

    ("Prosím o spätnú väzbu k prezentácii ktorú som poslal minulý týždeň.", 0),

    ("Váš kolega Peter Novák vám poslal dokument na zdieľanie cez Google Drive.", 0),

    ("Informatívna schôdza o plánovanej rekonštrukcii chodníkov bude 18.4.", 0),

    ("Oznamujeme zmenu čísla účtu pre platbu členského príspevku od januára.", 0),

    ("Kurz prvej pomoci pre verejnosť sa koná 25. marca od 9:00 v hasičiarni.", 0),

    ("Vaša sťažnosť na hluk bola postúpená príslušnému oddeleniu na riešenie.", 0),

    ("Prosím vyplňte anonymný dotazník spokojnosti so službami do piatku.", 0),

    ("Srdečne vás pozývame na výstavu fotografií miestnych umelcov v galérii.", 0),

    ("Oznamujeme predĺženie otváracích hodín knižnice v letných mesiacoch.", 0),

    ("Vaša rezervácia tenisového kurtu v sobotu o 10:00 je potvrdená.", 0),

    ("Prosím nezabudnite priniesť na zajtrajšie stretnutie podpísané dokumenty.", 0),

    ("Zasielame pozvánku na oslavy výročia firmy ktoré sa konajú 15. júna.", 0),

    # ── NOVÉ DOPLNKOVÉ ANGLICKÉ HAM ──────────────────────────────────────────

    ("Could you forward the meeting invite to the new team members?", 0),

    ("I've attached the invoice for last month's services. Please process.", 0),

    ("Just a reminder that the all-hands presentation is tomorrow at 2pm.", 0),

    ("Your test results came back normal. Schedule a follow-up in 6 months.", 0),

    ("The CI pipeline failed on the latest commit. Can you take a look?", 0),

    ("Lunch is on me today. Let me know what time works for you.", 0),

    ("Please find the updated terms of service attached for your records.", 0),

    ("The client wants the revised proposal by Thursday EOD.", 0),

    ("Your boarding pass for tomorrow's flight is attached as a PDF.", 0),

    ("The office kitchen will be cleaned Friday afternoon. Please tidy up.", 0),

    ("We need two volunteers for the charity run next Saturday. Any takers?", 0),

    ("The new hire will start Monday. Please help onboard them to the team.", 0),

    ("Your 401k contribution has been updated as requested.", 0),

    ("I'm having trouble accessing the shared drive. Can you check permissions?", 0),

    ("The design review meeting has been moved to 11am to avoid conflicts.", 0),

    ("Your feedback on the beta release would be greatly appreciated.", 0),

    ("Please remember to back up your work before the system update tonight.", 0),

    ("The road in front of the office is closed until 3pm. Plan accordingly.", 0),

    ("Marketing approved the campaign assets. We're ready to launch.", 0),

    ("Thank you for covering my shift on Tuesday. I owe you one!", 0),

    # ── NOVÉ DOPLNKOVÉ SLOVENSKÉ SPAM ────────────────────────────────────────

    ("Exkluzívna ponuka len pre vás! Zarobte 2000 EUR za víkend z domu!", 1),

    ("Pozor! Váš účet Revolut bol zablokovaný. Odomknite ho kliknutím tu!", 1),

    ("Výborná správa! Ste víťazom BMW X5. Potvrďte osobné údaje do 12 hodín!", 1),

    ("Záhadná metóda milionárov: Investujte 50 EUR, vyberte 5000 EUR za týždeň!", 1),

    ("Hľadáme testérov aplikácie. Platba 200 EUR denne. Registrujte sa hneď!", 1),

    ("Vaša kreditná karta je zablokovaná. Zadajte údaje na odblokovanie.", 1),

    ("ŠOKUJÚCE: Tento liek vylieči rakovinu. Vláda to skrýva. Objednajte!", 1),

    ("Získajte cestovný pas EÚ do 5 dní! Legálna cesta. Kontaktujte nás!", 1),

    ("Poistné plnenie 3200 EUR čaká na vyplatenie. Kliknite a preverte si to!", 1),

    ("Pomôžte nám previesť 8 miliónov EUR. Odmeníme vás 15 percentami!", 1),

    ("Bezplatný kurz angličtiny online! Certifikát Cambridge. Prihláste sa!", 1),

    ("Najnovší iPhone za 49 EUR pre prvých 50 zákazníkov! Objednajte teraz!", 1),

    ("Vaše auto má skrytú závadu. Stiahnite si správu a zistite čo hrozí!", 1),

    ("Zistite kto si prezerá váš profil na Facebooku! Kliknite tu!", 1),

    ("Ste dlžník? Zmažeme váš dlh úplne legálne. Volajte 0900 DLHY!", 1),

    ("Lieky na poteniu, únavu, bolesť kĺbov za zlomok ceny. Objednajte!", 1),

    ("Váš Spotify účet bude deaktivovaný. Obnovte predplatné kliknutím!", 1),

    ("Lotéria Slovakia: Váš lístok č. 847293 vyhral 75 000 EUR!", 1),

    ("Fotovoltika ZADARMO s dotáciou! Ušetrite 300 EUR mesačne. Kliknite!", 1),

    ("Sledujte prenos peňazí naživo! Váš preplatok 640 EUR čaká. Žiadajte!", 1),

    # ── EXTRA ANGLICKÝ SPAM ───────────────────────────────────────────────────

    ("Send $200 in gift cards to unlock your prize. Instructions inside!", 1),

    ("This is not a joke: you owe us $4,999. Pay or face legal action!", 1),

    ("LIMITED TIME: Solar panels installed FREE! Government rebate covers all!", 1),

    ("Your inheritance of $2.7 million is ready. Send processing fee now.", 1),

    ("Make $300 every hour watching videos online. No skills required!", 1),

    ("Special offer: Bulk medications shipped discreetly. No prescription!", 1),

    ("BREAKING OPPORTUNITY: Tesla insider stock tip before public announcement!", 1),

    ("Earn 200% returns in 48 hours with our forex trading algorithm!", 1),

    ("You have a secret admirer nearby! Click to see who it is!", 1),

    ("UNCLAIMED PACKAGE: Your parcel is held. Pay $3.50 release fee now!", 1),

    ("Guaranteed loans for people with bad credit. Apply in 60 seconds!", 1),

    ("Doctors reveal: This daily habit reverses aging by 15 years!", 1),

    ("Your Apple Pay was charged $499. Dispute this charge immediately!", 1),

    ("Click to see who unfriended you on Facebook. 100% free and accurate!", 1),

    ("Exclusive: Join our crypto pump group and earn $5000 this week!", 1),

    ("FREE home security system! Pay only shipping. Offer ends tonight!", 1),

    ("WARNING: We have your browsing history. Pay $500 or we expose you!", 1),

    ("Limited edition Rolex giveaway! First 10 replies win a free watch!", 1),

    ("You have been shortlisted for a $15,000 government assistance grant!", 1),

    ("AI investment bot earns $800/day autopilot. Signup fee just $99!", 1),

    ("Claim your free $200 Amazon voucher. Valid for the next 2 hours!", 1),

    ("Grow organic followers overnight. 50,000 TikTok fans guaranteed!", 1),

    ("Your package returned: address unverified. Update now to reschedule.", 1),

    ("Secret diet trick: Eat this one food before bed and lose belly fat!", 1),

    ("YOU are eligible for a student loan forgiveness of up to $20,000!", 1),

    ("ALERT: Your bank account has been accessed from Russia. Secure now!", 1),

    ("Real estate investment: 30% ROI in 3 months. Spots nearly filled!", 1),

    ("Part-time data entry: $22/hr, work from home, no experience needed!", 1),

    ("Your Venmo account flagged. Verify identity or funds will be frozen!", 1),

    ("Prescription glasses for $6.95! Free lenses included. Order today!", 1),

    # ── EXTRA ANGLICKÝ HAM ────────────────────────────────────────────────────

    ("I'll send over the revised budget spreadsheet by this afternoon.", 0),

    ("The team building event is scheduled for the last Friday of this month.", 0),

    ("Could you add me to the project Slack channel when you get a chance?", 0),

    ("The access credentials for the staging environment are in LastPass.", 0),

    ("Please make sure to test the payment flow before tomorrow's demo.", 0),

    ("Your order has been picked and will ship within 2 business days.", 0),

    ("The quarterly targets were discussed in today's leadership call.", 0),

    ("Hi Sarah, just confirming our coffee catch-up tomorrow at 10am.", 0),

    ("The HR portal is now open for benefits enrollment until November 30.", 0),

    ("Your library fine of $1.50 has been cleared. Enjoy your next borrow!", 0),

    ("Please rate your recent experience with our support team.", 0),

    ("The project wiki has been updated with the latest architecture diagrams.", 0),

    ("I noticed a discrepancy in the invoices from last quarter. Can we review?", 0),

    ("Your electric bill for October is available to view in the online portal.", 0),

    ("The annual company survey is now live. Please take 5 minutes to respond.", 0),

    ("Following up on the proposal I sent last Tuesday. Any thoughts?", 0),

    ("New bike lanes are being installed on the main road starting Monday.", 0),

    ("Your child has been placed on the waitlist for the summer program.", 0),

    ("We've updated our app. Please update to version 4.2 for new features.", 0),

    ("The water heater installation is complete. All systems are working.", 0),

    ("Please RSVP to the end-of-year banquet by December 10th.", 0),

    ("Your refund of $47.99 has been processed and should arrive in 5 days.", 0),

    ("The board approved the merger. Further details will be shared Monday.", 0),

    ("Thank you for volunteering at the community clean-up last Saturday!", 0),

    ("Can you review the onboarding checklist before the new hire starts?", 0),

    ("Our internet service will be down for maintenance Sunday 1-3am.", 0),

    ("The new parking structure opens next week. Permits available online.", 0),

    ("Your annual eye exam is due. Book an appointment with your optometrist.", 0),

    ("The vendor contract has been signed. Work begins the first of next month.", 0),

    ("I've uploaded all the photos from the event to the shared Google Drive.", 0),

    # ── EXTRA SLOVENSKÝ HAM ───────────────────────────────────────────────────

    ("Pripomíname vám stretnutie výboru samosprávy v utorok o 18:30.", 0),

    ("Vaša platba za energie bola spracovaná. Ďalší výpis 15. februára.", 0),

    ("Záhradná slavnosť v parku sa koná v nedeľu o 15:00. Vstup voľný.", 0),

    ("Zbierka oblečenia pre útulok prebieha do konca mesiaca. Ďakujeme!", 0),

    ("Prosím pošlite podpísaný súhlas so spracovaním osobných údajov.", 0),

    ("Tréning dobrovoľných hasičov je v sobotu o 9:00 na požiarnej stanici.", 0),

    ("Váš pas je pripravený na vyzdvihnutie na oddelení dokladov.", 0),

    ("Výsledky komunálnych volieb sú zverejnené na webe obce.", 0),

    ("Prerušenie dodávky elektriny na ulici Dlhá: streda 9:00-13:00.", 0),

    ("Novela zákona o DPH platí od januára. Prečítajte si zmeny v prílohe.", 0),

    ("Výzva na predloženie ponúk: zákazka na kosenie verejnej zelene.", 0),

    ("Váš žiak bol ospravedlnený z hodiny telesnej výchovy dňa 12.3.", 0),

    ("Spolok záhradkárov oznamuje výšku členského príspevku na rok 2024.", 0),

    ("Vaša rezervácia squash kurtu č. 3 na piatok 18:00 je potvrdená.", 0),

    ("Obecný úrad: Žiadosť o vydanie stavebného povolenia bola prijatá.", 0),

    ("Zasielame vám ročný výkaz spotreby tepla pre vyúčtovanie nákladov.", 0),

    ("Konferencia o digitalizácii verejnej správy sa koná 20.-21. mája.", 0),

    ("Vaše miesto v materskej škole je rezervované od septembra 2024.", 0),

    ("Letná škola programovania pre deti: prihlásenie otvorené do 30.4.", 0),

    ("Zmena úradných hodín mestského úradu platí od prvého marca.", 0),

]

def populate_sample_data(conn: sqlite3.Connection) -> None:

    count = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]

    if count == 0:

        log.info("Populujem databázu dátami (%d e-mailov)...", len(SAMPLE_EMAILS))

        for text, label in SAMPLE_EMAILS:

            save_email(conn, text, label, source="dataset")

        log.info("Dáta načítané.")

# ─────────────────────────────────────────────────────────────────────────────

# CLI

# ─────────────────────────────────────────────────────────────────────────────

def cli_main():

    print("\n" + "="*60)

    print(" SPAM FILTER")

    print("="*60)

    conn = init_db()

    populate_sample_data(conn)

    pipeline = load_model()

    if pipeline is None:

        print("\nTrénujem model...")

        texts, labels = load_all_emails(conn)

        pipeline, accuracy, report = train_model(texts, labels)

        save_model(pipeline)

        update_stats(conn, accuracy, len(labels), sum(labels), len(labels)-sum(labels))

        print(f"Model natrénovaný! Presnosť: {accuracy*100:.2f}%")

    while True:

        print("\n1) Klasifikovať 2) Štatistiky 3) Retréning 4) Koniec")

        choice = input("Výber: ").strip()

        if choice == "1":

            text = input("Email text: ")

            label, conf = predict(pipeline, text)

            print(f"Výsledok: {label.upper()} ({conf*100:.1f}%)")

        elif choice == "2":

            print(get_stats(conn))

        elif choice == "3":

            texts, labels = load_all_emails(conn)

            pipeline, accuracy, report = train_model(texts, labels)

            save_model(pipeline)

            print(f"Presnosť: {accuracy*100:.2f}%\n{report}")

        elif choice == "4":

            break

    conn.close()

if __name__ == "__main__":

    cli_main()
