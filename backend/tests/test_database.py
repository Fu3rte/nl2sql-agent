"""Test database module: init, schema text, schema info, connections."""

import sqlite3
import app.database as db


class TestDatabaseInit:
    def test_tables_created(self):
        """After init_db, all 4 tables should exist."""
        conn = db.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        conn.close()
        names = {row["name"] for row in tables}
        assert names == {"customers", "products", "orders", "order_items"}

    def test_seed_data_customers(self):
        """Should have exactly 20 customers."""
        conn = db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        conn.close()
        assert count == 20

    def test_seed_data_orders(self):
        """Should have exactly 30 orders."""
        conn = db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        conn.close()
        assert count == 30

    def test_seed_data_products(self):
        """Should have exactly 15 products."""
        conn = db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        conn.close()
        assert count == 15

    def test_idempotent_init(self):
        """Calling init_db twice should not duplicate data."""
        db.init_db()
        db.init_db()
        conn = db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        conn.close()
        assert count == 20


class TestGetSchemaInfo:
    def test_returns_correct_structure(self):
        info = db.get_schema_info()
        assert len(info) == 4
        for table in info:
            assert "name" in table
            assert "columns" in table
            assert isinstance(table["columns"], list)
            for col in table["columns"]:
                assert "name" in col
                assert "type" in col

    def test_customers_columns(self):
        info = db.get_schema_info()
        cust = next(t for t in info if t["name"] == "customers")
        col_names = {c["name"] for c in cust["columns"]}
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "city" in col_names
        assert "created_at" in col_names


class TestGetSchemaText:
    def test_includes_all_tables(self):
        text = db.get_schema_text()
        assert "CREATE TABLE customers" in text
        assert "CREATE TABLE products" in text
        assert "CREATE TABLE orders" in text
        assert "CREATE TABLE order_items" in text

    def test_includes_sample_rows(self):
        text = db.get_schema_text()
        assert "Sample rows" in text

    def test_excludes_sqlite_system_tables(self):
        text = db.get_schema_text()
        assert "sqlite_" not in text


class TestGetConnection:
    def test_row_factory_is_set(self):
        conn = db.get_connection()
        cursor = conn.execute("SELECT 1 AS val")
        row = cursor.fetchone()
        conn.close()
        assert row["val"] == 1
        assert isinstance(row, sqlite3.Row)
