import os
import sqlite3
import subprocess
import logging
import sys

from pathlib import Path
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from main import main as normalize_pipeline


# ---------------- CONFIG ----------------

PARSERS_DIR = Path("Parsing")

NORMALIZED_DB = "normalized_guitars.db"

DB_TABLE = "guitars"

LOG_FILE = "weekly_update.log"


# ---------------- LOGGING ----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ---------------- FIND PARSERS ----------------

def find_parser_scripts():

    parser_files = []

    for file in PARSERS_DIR.rglob("*.py"):

        if file.name.startswith("__"):
            continue

        if file.name in [
            "main.py",
            "normalizer.py",
            "update.py"
        ]:
            continue

        parser_files.append(file)

    return parser_files


# ---------------- DATABASE PATH ----------------

def get_database_path(parser_path: Path):

    """
    Для:
    Parsing/Thomann/parser.py

    вернет:
    Parsing/Thomann/thomann.db
    """

    folder_name = parser_path.parent.name.lower()

    db_name = f"{folder_name}.db"

    return parser_path.parent / db_name


# ---------------- CLEAR DATABASE ----------------

def clear_database(db_path: Path):

    try:

        if not db_path.exists():
            return

        conn = sqlite3.connect(db_path)

        cursor = conn.cursor()

        cursor.execute(
            f"DROP TABLE IF EXISTS {DB_TABLE}"
        )

        conn.commit()

        conn.close()

        logger.info(
            f"[CLEARED] {db_path}"
        )

    except Exception as e:

        logger.error(
            f"[ERROR] {db_path}: {e}"
        )


# ---------------- RUN PARSERS ----------------

def run_parsers():

    parsers = find_parser_scripts()

    if not parsers:

        logger.error(
            "No parser scripts found"
        )

        return

    logger.info(
        f"Found {len(parsers)} parsers"
    )

    for parser in parsers:

        try:

            db_path = get_database_path(parser)

            # Удаляем старую БД магазина
            clear_database(db_path)

            logger.info(
                f"[RUNNING] {parser.name}"
            )

            # Передаем путь БД в parser
            result = subprocess.run(
                [
                    sys.executable,
                    str(parser.resolve()),
                    str(db_path.resolve())
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            if result.returncode == 0:

                logger.info(
                    f"[SUCCESS] {parser.name}"
                )

                logger.info(
                    f"[DB SAVED] {db_path}"
                )

            else:

                logger.error(
                    f"[FAILED] {parser.name}"
                )

                logger.error(
                    result.stderr
                )

        except Exception as e:

            logger.error(
                f"[ERROR] {parser.name}: {e}"
            )


# ---------------- CLEAR NORMALIZED DB ----------------

def clear_normalized_db():

    if os.path.exists(NORMALIZED_DB):

        try:

            conn = sqlite3.connect(
                NORMALIZED_DB
            )

            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM guitars"
            )

            conn.commit()
            conn.close()

            logger.info(
                f"[REMOVED] {NORMALIZED_DB}"
            )

        except Exception as e:

            logger.error(
                f"[ERROR] {NORMALIZED_DB}: {e}"
            )


# ---------------- UPDATE PIPELINE ----------------

def update_pipeline():

    logger.info(
        "=========================="
    )

    logger.info(
        "STARTING WEEKLY UPDATE"
    )

    logger.info(
        "=========================="
    )

    start = datetime.now()

    try:

        # STEP 1
        logger.info(
            "STEP 1: Clearing normalized DB"
        )

        clear_normalized_db()

        # STEP 2
        logger.info(
            "STEP 2: Running parsers"
        )

        run_parsers()

        # STEP 3
        logger.info(
            "STEP 3: Running normalization"
        )

        normalize_pipeline()

        logger.info(
            "[SUCCESS] "
            "Normalized DB updated"
        )

    except Exception as e:

        logger.exception(
            f"[CRITICAL ERROR] {e}"
        )

    finish = datetime.now()

    logger.info(
        f"Finished in: {finish - start}"
    )

    logger.info(
        "=========================="
    )


# ---------------- SCHEDULER ----------------

def start_scheduler():

    scheduler = BlockingScheduler()

    scheduler.add_job(
        update_pipeline,
        trigger="interval",
        weeks=1,
        next_run_time=datetime.now()
    )

    logger.info(
        "Scheduler started"
    )

    logger.info(
        "Update interval: 1 week"
    )

    try:

        scheduler.start()

    except (
        KeyboardInterrupt,
        SystemExit
    ):

        logger.info(
            "Scheduler stopped"
        )


# ---------------- MAIN ----------------

if __name__ == "__main__":

    start_scheduler()