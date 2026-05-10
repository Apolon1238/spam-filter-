"""
=============================================================
  Flask Backend pre Spam Filter AI
=============================================================
Spustenie:
    pip install flask scikit-learn numpy
    python app.py

Potom otvor: http://localhost:5000
"""

import os
import sqlite3
import logging
from flask import Flask, request, jsonify, send_from_directory, g

# Import všetkých funkcií zo spam filtra
from spam_filter import (
    init_db, populate_sample_data,
    load_model, save_model, train_model,
    load_all_emails, save_email, save_correction, update_stats,
    get_stats, predict, DB_PATH
)

# ── Nastavenie ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder=".")

# Globálny model
pipeline = None


def get_conn():
    """Vráti DB spojenie pre aktuálny request (vytvorí ak neexistuje)."""
    if "conn" not in g:
        g.conn = sqlite3.connect(DB_PATH)
    return g.conn


@app.teardown_appcontext
def close_conn(exception):
    """Zatvorí DB spojenie po každom requeste."""
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()


def init_app():
    """Inicializácia DB a modelu pri štarte servera."""
    global pipeline

    tmp_conn = init_db()
    populate_sample_data(tmp_conn)
    pipeline = load_model()

    if pipeline is None:
        log.info("Model neexistuje – trénujem na základných dátach...")
        texts, labels = load_all_emails(tmp_conn)
        pipeline, accuracy, _ = train_model(texts, labels)
        save_model(pipeline)
        spam_count = sum(labels)
        ham_count  = len(labels) - spam_count
        update_stats(tmp_conn, accuracy, len(labels), spam_count, ham_count)
        log.info("Model natrénovaný. Presnosť: %.2f%%", accuracy * 100)
    else:
        log.info("Model načítaný z disku.")

    tmp_conn.close()


# ── Statické súbory ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ── API endpointy ─────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status"     : "ok",
        "model_ready": pipeline is not None
    })


@app.route("/api/stats", methods=["GET"])
def stats():
    try:
        data = get_stats(get_conn())
        return jsonify(data)
    except Exception as e:
        log.exception("Chyba pri načítaní štatistík")
        return jsonify({"error": str(e)}), 500


@app.route("/api/classify", methods=["POST"])
def classify():
    global pipeline

    if pipeline is None:
        return jsonify({"error": "Model nie je pripravený. Skúste /api/retrain."}), 503

    body = request.get_json(silent=True)
    if not body or not body.get("text", "").strip():
        return jsonify({"error": "Chýba pole 'text'."}), 400

    text = body["text"].strip()

    try:
        label, confidence = predict(pipeline, text)
        return jsonify({
            "label"     : label,
            "is_spam"   : label == "spam",
            "confidence": round(confidence * 100, 1)
        })
    except Exception as e:
        log.exception("Chyba pri klasifikácii")
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def feedback():
    global pipeline

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Chýba JSON telo."}), 400

    text       = body.get("text", "").strip()
    predicted  = body.get("predicted", "")
    is_correct = body.get("is_correct", True)

    if not text or predicted not in ("spam", "ham"):
        return jsonify({"error": "Neplatné parametre."}), 400

    predicted_int = 1 if predicted == "spam" else 0
    conn = get_conn()

    if is_correct:
        save_email(conn, text, predicted_int, source="user_confirmed")
        return jsonify({"saved": True, "retrained": False, "new_accuracy": None})
    else:
        correct_int = 1 - predicted_int
        save_correction(conn, text, predicted_int, correct_int)

        try:
            texts, labels = load_all_emails(conn)
            pipeline, accuracy, _ = train_model(texts, labels)
            save_model(pipeline)
            spam_count = sum(labels)
            ham_count  = len(labels) - spam_count
            update_stats(conn, accuracy, len(labels), spam_count, ham_count)
            return jsonify({
                "saved"       : True,
                "retrained"   : True,
                "new_accuracy": round(accuracy * 100, 2)
            })
        except Exception as e:
            log.exception("Chyba pri dotrénovaní")
            return jsonify({"saved": True, "retrained": False, "new_accuracy": None})


@app.route("/api/retrain", methods=["POST"])
def retrain():
    global pipeline

    try:
        conn = get_conn()
        texts, labels = load_all_emails(conn)
        pipeline, accuracy, _ = train_model(texts, labels)
        save_model(pipeline)
        spam_count = sum(labels)
        ham_count  = len(labels) - spam_count
        update_stats(conn, accuracy, len(labels), spam_count, ham_count)
        return jsonify({
            "accuracy": round(accuracy * 100, 2),
            "total"   : len(labels),
            "spam"    : spam_count,
            "ham"     : ham_count
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log.exception("Chyba pri trénovaní")
        return jsonify({"error": str(e)}), 500


# ── Spustenie ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_app()
    log.info("Server štartuje na http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
