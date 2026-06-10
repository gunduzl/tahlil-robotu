"""SQLite veritabani islemleri."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "tahlil.db"


def get_connection() -> sqlite3.Connection:
    """Veritabani baglantisini olusturur."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def init_db() -> None:
    """Gerekli tablolari olusturur."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS TestResults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                test_date TEXT NOT NULL,
                test_name TEXT NOT NULL,
                test_value REAL NOT NULL,
                unit TEXT NOT NULL,
                status TEXT NOT NULL,
                reference_text TEXT NOT NULL,
                is_out_of_range INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
            );
            """
        )


def create_user(name: str, age: int, gender: str) -> int:
    """Yeni kullanici kaydi ekler."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO Users (name, age, gender)
            VALUES (?, ?, ?)
            """,
            (name.strip(), age, gender),
        )
        return int(cursor.lastrowid)


def get_users() -> list[dict[str, Any]]:
    """Tum kullanicilari listeler."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, age, gender FROM Users ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]


def get_user(user_id: int) -> dict[str, Any] | None:
    """Tek bir kullaniciyi dondurur."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, name, age, gender FROM Users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def update_user(user_id: int, name: str, age: int, gender: str) -> bool:
    """Kullanici bilgisini gunceller."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE Users
            SET name = ?, age = ?, gender = ?
            WHERE id = ?
            """,
            (name.strip(), age, gender, user_id),
        )
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    """Kullaniciyi ve bagli tum tahlillerini siler."""
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM Users WHERE id = ?", (user_id,))
        return cursor.rowcount > 0


def create_test_result(
    user_id: int,
    test_date: str,
    test_name: str,
    test_value: float,
    unit: str,
    status: str,
    reference_text: str,
    is_out_of_range: bool,
) -> int:
    """Yeni tahlil sonucu ekler."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO TestResults (
                user_id,
                test_date,
                test_name,
                test_value,
                unit,
                status,
                reference_text,
                is_out_of_range
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                test_date,
                test_name.strip(),
                test_value,
                unit.strip(),
                status,
                reference_text,
                int(is_out_of_range),
            ),
        )
        return int(cursor.lastrowid)


def get_test_results_by_user(user_id: int) -> list[dict[str, Any]]:
    """Kullaniciya ait tum tahlilleri tarih bazli getirir."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                user_id,
                test_date,
                test_name,
                test_value,
                unit,
                status,
                reference_text,
                is_out_of_range
            FROM TestResults
            WHERE user_id = ?
            ORDER BY test_date DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_test_result(
    result_id: int,
    test_date: str,
    test_name: str,
    test_value: float,
    unit: str,
    status: str,
    reference_text: str,
    is_out_of_range: bool,
) -> bool:
    """Tahlil sonucunu gunceller."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE TestResults
            SET
                test_date = ?,
                test_name = ?,
                test_value = ?,
                unit = ?,
                status = ?,
                reference_text = ?,
                is_out_of_range = ?
            WHERE id = ?
            """,
            (
                test_date,
                test_name.strip(),
                test_value,
                unit.strip(),
                status,
                reference_text,
                int(is_out_of_range),
                result_id,
            ),
        )
        return cursor.rowcount > 0


def delete_test_result(result_id: int) -> bool:
    """Tek bir tahlil sonucunu siler."""
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM TestResults WHERE id = ?", (result_id,))
        return cursor.rowcount > 0
