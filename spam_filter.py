"""
=============================================================
  Inteligentný Spam Filter s Naivným Bayesom a Učením zo Chýb
=============================================================
Autor: AI Asistent
Popis: Spam filter využívajúci strojové učenie (TF-IDF + Multinomial Naive Bayes)
       s mechanizmom spätnej väzby a inkrementálneho učenia.
"""

import os
import json
import sqlite3
import pickle
import re
import logging
from datetime import datetime
from typing import Tuple, Dict, Any

import numpy as np
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix
)
from sklearn.pipeline import Pipeline

# --- Nastavenie logovania ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# --- Cesty k súborom ---
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "spam_filter.db")
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")


# ─────────────────────────────────────────────────────────────────────────────
#  DATABÁZA
# ─────────────────────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    """
    Inicializácia SQLite databázy.
    Tabuľky:
      - emails   : všetky e-maily (text, label, zdroj, čas)
      - corrections: opravy od používateľa (chybné predikcie)
      - stats    : súhrnné štatistiky
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS emails (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            text      TEXT    NOT NULL,
            label     INTEGER NOT NULL,   -- 0=ham, 1=spam
            source    TEXT    DEFAULT 'dataset',
            created   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS corrections (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email_text    TEXT    NOT NULL,
            predicted     INTEGER NOT NULL,
            correct_label INTEGER NOT NULL,
            created       TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            total_emails    INTEGER DEFAULT 0,
            spam_count      INTEGER DEFAULT 0,
            ham_count       INTEGER DEFAULT 0,
            corrections     INTEGER DEFAULT 0,
            model_accuracy  REAL    DEFAULT 0.0,
            last_trained    TEXT    DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO stats (id) VALUES (1);
    """)
    conn.commit()
    return conn


def save_email(conn: sqlite3.Connection,
               text: str, label: int, source: str = "user") -> None:
    """Uloží e-mail do databázy."""
    conn.execute(
        "INSERT INTO emails (text, label, source) VALUES (?, ?, ?)",
        (text, label, source)
    )
    conn.commit()


def save_correction(conn: sqlite3.Connection,
                    text: str, predicted: int, correct: int) -> None:
    """Uloží opravu (chybná predikcia) do databázy."""
    conn.execute(
        "INSERT INTO corrections (email_text, predicted, correct_label) "
        "VALUES (?, ?, ?)",
        (text, predicted, correct)
    )
    # Zároveň ulož e-mail so správnym labelom pre ďalší tréning
    save_email(conn, text, correct, source="correction")
    # Inkrementuj počítadlo korekcií
    conn.execute("UPDATE stats SET corrections = corrections + 1 WHERE id = 1")
    conn.commit()


def update_stats(conn: sqlite3.Connection,
                 accuracy: float,
                 total: int, spam: int, ham: int) -> None:
    """Aktualizuje štatistiky po trénovaní modelu."""
    conn.execute(
        """UPDATE stats
           SET total_emails = ?, spam_count = ?, ham_count = ?,
               model_accuracy = ?, last_trained = datetime('now')
           WHERE id = 1""",
        (total, spam, ham, accuracy)
    )
    conn.commit()


def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Vráti aktuálne štatistiky zo databázy."""
    row = conn.execute("SELECT * FROM stats WHERE id = 1").fetchone()
    corrections = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
    if row:
        return {
            "total_emails"   : row[1],
            "spam_count"     : row[2],
            "ham_count"      : row[3],
            "corrections"    : corrections,
            "model_accuracy" : round(row[5] * 100, 2),
            "last_trained"   : row[6],
        }
    return {}


def load_all_emails(conn: sqlite3.Connection):
    """Načíta všetky e-maily z databázy pre tréning."""
    rows = conn.execute("SELECT text, label FROM emails").fetchall()
    texts  = [r[0] for r in rows]
    labels = [r[1] for r in rows]
    return texts, labels


# ─────────────────────────────────────────────────────────────────────────────
#  PREDSPRACOVANIE TEXTU  (NLP)
# ─────────────────────────────────────────────────────────────────────────────

# Anglické stop slová (rozšírená sada)
STOP_WORDS = {
    "a","about","above","after","again","against","all","am","an","and",
    "any","are","aren't","as","at","be","because","been","before","being",
    "below","between","both","but","by","can't","cannot","could","couldn't",
    "did","didn't","do","does","doesn't","doing","don't","down","during",
    "each","few","for","from","further","get","got","had","hadn't","has",
    "hasn't","have","haven't","having","he","he'd","he'll","he's","her",
    "here","here's","hers","herself","him","himself","his","how","how's",
    "i","i'd","i'll","i'm","i've","if","in","into","is","isn't","it",
    "it's","its","itself","let's","me","more","most","mustn't","my",
    "myself","no","nor","not","of","off","on","once","only","or","other",
    "ought","our","ours","ourselves","out","over","own","same","shan't",
    "she","she'd","she'll","she's","should","shouldn't","so","some","such",
    "than","that","that's","the","their","theirs","them","themselves","then",
    "there","there's","these","they","they'd","they'll","they're","they've",
    "this","those","through","to","too","under","until","up","very","was",
    "wasn't","we","we'd","we'll","we're","we've","were","weren't","what",
    "what's","when","when's","where","where's","which","while","who","who's",
    "whom","why","why's","will","with","won't","would","wouldn't","you",
    "you'd","you'll","you're","you've","your","yours","yourself","yourselves"
}

def preprocess(text: str) -> str:
    """
    NLP predspracovanie textu:
      1. Malé písmená
      2. Odstránenie špeciálnych znakov a čísel
      3. Tokenizácia (rozdelenie na slová)
      4. Odstránenie stop slov
      5. Znovuzloženie do reťazca
    """
    # 1. Malé písmená
    text = text.lower()
    # 2. Odstránenie URL adries
    text = re.sub(r'http\S+|www\S+', ' url ', text)
    # 3. Odstránenie e-mailových adries
    text = re.sub(r'\S+@\S+', ' email ', text)
    # 4. Nahradenie čísel
    text = re.sub(r'\d+', ' num ', text)
    # 5. Odstránenie špeciálnych znakov
    text = re.sub(r'[^a-z\s]', ' ', text)
    # 6. Tokenizácia
    tokens = text.split()
    # 7. Odstránenie stop slov a krátkych tokenov
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
    return " ".join(tokens)


# ─────────────────────────────────────────────────────────────────────────────
#  MODEL
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline() -> Pipeline:
    """
    Vytvorí sklearn Pipeline:
      TfidfVectorizer → MultinomialNaiveBayes
    TF-IDF: Term Frequency – Inverse Document Frequency
      - oceňuje slová, ktoré sú dôležité pre konkrétny dokument,
        ale nie sú príliš časté vo všetkých dokumentoch.
    Multinomial Naive Bayes:
      - pravdepodobnostný klasifikátor vhodný pre textové dáta,
        rýchly a efektívny aj na menších datasetoch.
    """
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            preprocessor=preprocess,   # vlastné predspracovanie
            ngram_range=(1, 2),        # unigramy aj bigramy
            max_features=15_000,       # max. počet features
            sublinear_tf=True,         # log škálovanie TF
        )),
        ("clf", MultinomialNB(alpha=0.1))  # Laplace smoothing
    ])


def train_model(texts, labels) -> Tuple[Pipeline, float, str]:
    """
    Trénuje model a vracia (pipeline, accuracy, report).
    Ak je dostatok dát, rozdelí ich na train/test 80/20.
    """
    if len(texts) < 10:
        raise ValueError("Príliš málo dát na tréning (min. 10 e-mailov).")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred   = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report   = classification_report(
        y_test, y_pred,
        target_names=["Ham (legitímny)", "Spam"],
        zero_division=0
    )
    log.info("Tréning dokončený. Presnosť: %.2f%%", accuracy * 100)
    return pipeline, accuracy, report


def save_model(pipeline: Pipeline) -> None:
    """Uloží natrénovaný model na disk (pickle)."""
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    log.info("Model uložený: %s", MODEL_PATH)


def load_model() -> Pipeline | None:
    """Načíta model z disku, ak existuje."""
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None


def predict(pipeline: Pipeline, text: str) -> Tuple[str, float]:
    """
    Klasifikuje jeden e-mail.
    Vracia (label, confidence) kde label je 'spam' alebo 'ham'.
    """
    proba = pipeline.predict_proba([text])[0]
    pred  = pipeline.predict([text])[0]
    label = "spam" if pred == 1 else "ham"
    conf  = proba[pred]
    return label, float(conf)


# ─────────────────────────────────────────────────────────────────────────────
#  VZOROVÝ DATASET
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_EMAILS = [
    # SPAM
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

    # HAM (legitímne)
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
]


def populate_sample_data(conn: sqlite3.Connection) -> None:
    """Naplní databázu vzorovými dátami, ak je prázdna."""
    count = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    if count == 0:
        log.info("Populujem databázu vzorovými dátami (%d e-mailov)...",
                 len(SAMPLE_EMAILS))
        for text, label in SAMPLE_EMAILS:
            save_email(conn, text, label, source="dataset")
        log.info("Vzorové dáta načítané.")


# ─────────────────────────────────────────────────────────────────────────────
#  CLI ROZHRANIE
# ─────────────────────────────────────────────────────────────────────────────

def cli_main():
    """Hlavná slučka CLI rozhrania."""
    print("\n" + "="*60)
    print("   🛡️  INTELIGENTNÝ SPAM FILTER  🛡️")
    print("="*60)

    # Inicializácia
    conn     = init_db()
    populate_sample_data(conn)
    pipeline = load_model()

    # Prvý tréning, ak model neexistuje
    if pipeline is None:
        print("\n⚙️  Trénujem model na základných dátach...")
        texts, labels = load_all_emails(conn)
        pipeline, accuracy, report = train_model(texts, labels)
        save_model(pipeline)
        spam_count = sum(labels)
        ham_count  = len(labels) - spam_count
        update_stats(conn, accuracy, len(labels), spam_count, ham_count)
        print(f"\n✅ Model natrénovaný! Presnosť: {accuracy*100:.2f}%")
        print(report)

    # Hlavná slučka
    while True:
        print("\n" + "-"*60)
        print("MENU:")
        print("  1) Klasifikovať e-mail")
        print("  2) Zobraziť štatistiky")
        print("  3) Znovu natrénovať model")
        print("  4) Ukončiť")
        print("-"*60)
        choice = input("Výber: ").strip()

        # ── Klasifikácia ──────────────────────────────────────────
        if choice == "1":
            print("\nZadajte text e-mailu (Enter 2x pre potvrdenie):")
            lines = []
            while True:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)
            email_text = "\n".join(lines)

            if not email_text.strip():
                print("⚠️  Prázdny text, skúste znova.")
                continue

            label, confidence = predict(pipeline, email_text)
            icon  = "🚨" if label == "spam" else "✅"
            label_sk = "SPAM" if label == "spam" else "LEGITÍMNY"

            print(f"\n{icon}  Výsledok: {label_sk}")
            print(f"   Istota: {confidence*100:.1f}%")

            # Spätná väzba
            fb = input("\nJe tento výsledok správny? (a/n): ").strip().lower()
            if fb == "n":
                correct_label = 0 if label == "spam" else 1
                save_correction(conn, email_text,
                                1 if label == "spam" else 0,
                                correct_label)
                print("💾 Oprava uložená. Dotrénujem model...")

                # Inkrementálne doučenie
                texts, labels_all = load_all_emails(conn)
                pipeline, accuracy, _ = train_model(texts, labels_all)
                save_model(pipeline)
                spam_count = sum(labels_all)
                ham_count  = len(labels_all) - spam_count
                update_stats(conn, accuracy,
                             len(labels_all), spam_count, ham_count)
                print(f"✅ Model aktualizovaný. Nová presnosť: {accuracy*100:.2f}%")
            else:
                print("👍 Super! Klasifikácia bola správna.")
                save_email(conn, email_text,
                           1 if label == "spam" else 0, source="user_confirmed")

        # ── Štatistiky ────────────────────────────────────────────
        elif choice == "2":
            stats = get_stats(conn)
            print("\n📊 ŠTATISTIKY SPAM FILTRA")
            print(f"   Celkový počet e-mailov : {stats.get('total_emails', 0)}")
            print(f"   Spam e-maily           : {stats.get('spam_count', 0)}")
            print(f"   Legitímne e-maily      : {stats.get('ham_count', 0)}")
            print(f"   Počet opravených chýb  : {stats.get('corrections', 0)}")
            print(f"   Presnosť modelu        : {stats.get('model_accuracy', 0)}%")
            print(f"   Posledný tréning       : {stats.get('last_trained', 'N/A')}")

        # ── Manuálny retréning ────────────────────────────────────
        elif choice == "3":
            print("\n⚙️  Trénujem model na všetkých dostupných dátach...")
            texts, labels_all = load_all_emails(conn)
            pipeline, accuracy, report = train_model(texts, labels_all)
            save_model(pipeline)
            spam_count = sum(labels_all)
            ham_count  = len(labels_all) - spam_count
            update_stats(conn, accuracy, len(labels_all), spam_count, ham_count)
            print(f"✅ Model natrénovaný! Presnosť: {accuracy*100:.2f}%")
            print(report)

        elif choice == "4":
            print("\n👋 Dovidenia!")
            break
        else:
            print("⚠️  Neplatná voľba. Skúste znova.")

    conn.close()


if __name__ == "__main__":
    cli_main()
