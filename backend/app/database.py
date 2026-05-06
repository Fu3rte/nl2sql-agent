import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ecommerce.db")

CREATE_TABLES_SQL = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    city TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date TEXT NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'completed'
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL
);
"""

SEED_DATA_SQL = """
-- 20 customers from 5 cities
INSERT INTO customers (name, email, city) VALUES
('张伟', 'zhangwei@email.com', '北京'),
('李娜', 'lina@email.com', '上海'),
('王强', 'wangqiang@email.com', '广州'),
('赵敏', 'zhaomin@email.com', '深圳'),
('刘洋', 'liuyang@email.com', '杭州'),
('陈静', 'chenjing@email.com', '北京'),
('杨帆', 'yangfan@email.com', '上海'),
('黄丽', 'huangli@email.com', '广州'),
('周杰', 'zhoujie@email.com', '深圳'),
('吴芳', 'wufang@email.com', '杭州'),
('孙鹏', 'sunpeng@email.com', '北京'),
('马玲', 'maling@email.com', '上海'),
('朱峰', 'zhufeng@email.com', '广州'),
('胡雪', 'huxue@email.com', '深圳'),
('林涛', 'lintao@email.com', '杭州'),
('何梅', 'hemei@email.com', '北京'),
('郭瑞', 'guorui@email.com', '上海'),
('徐凯', 'xukai@email.com', '广州'),
('梁晓', 'liangxiao@email.com', '深圳'),
('宋雨', 'songyu@email.com', '杭州');

-- 15 products in 4 categories
INSERT INTO products (name, category, price, stock) VALUES
('iPhone 15', '电子产品', 6999.00, 50),
('MacBook Pro', '电子产品', 14999.00, 30),
('AirPods Pro', '电子产品', 1999.00, 100),
('iPad Air', '电子产品', 4999.00, 40),
('牛仔裤', '服装', 299.00, 200),
('羽绒服', '服装', 899.00, 80),
('运动鞋', '服装', 599.00, 150),
('T恤衫', '服装', 99.00, 300),
('有机大米', '食品', 49.90, 500),
('橄榄油', '食品', 89.00, 200),
('坚果礼盒', '食品', 168.00, 120),
('进口咖啡', '食品', 128.00, 90),
('乳胶枕', '家居', 399.00, 60),
('智能台灯', '家居', 259.00, 45),
('收纳箱', '家居', 79.00, 180);

-- 30 orders over ~3 months
INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
(1, '2026-03-15', 8998.00, 'completed'),
(2, '2026-03-16', 599.00, 'completed'),
(3, '2026-03-17', 14999.00, 'completed'),
(4, '2026-03-18', 49.90, 'completed'),
(5, '2026-03-20', 299.00, 'completed'),
(6, '2026-03-22', 6198.00, 'returned'),
(7, '2026-03-25', 128.00, 'completed'),
(8, '2026-03-28', 399.00, 'completed'),
(1, '2026-04-01', 1999.00, 'completed'),
(2, '2026-04-02', 89.00, 'completed'),
(3, '2026-04-05', 259.00, 'completed'),
(4, '2026-04-08', 8997.00, 'completed'),
(5, '2026-04-10', 168.00, 'completed'),
(9, '2026-04-11', 6999.00, 'completed'),
(10, '2026-04-12', 299.00, 'completed'),
(11, '2026-04-13', 14999.00, 'returned'),
(12, '2026-04-15', 1999.00, 'completed'),
(13, '2026-04-18', 49.90, 'completed'),
(14, '2026-04-20', 899.00, 'completed'),
(15, '2026-04-22', 128.00, 'completed'),
(9, '2026-05-01', 399.00, 'completed'),
(10, '2026-05-02', 259.00, 'completed'),
(11, '2026-05-03', 599.00, 'completed'),
(16, '2026-05-04', 4999.00, 'completed'),
(17, '2026-05-05', 79.00, 'completed'),
(1, '2026-05-06', 198.00, 'completed'),
(2, '2026-05-06', 10875.00, 'returned'),
(5, '2026-05-06', 6287.00, 'returned'),
(8, '2026-05-06', 6999.00, 'completed'),
(12, '2026-05-06', 168.00, 'completed');

-- ~80 order_items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 6999.00, 6999.00),
(1, 3, 1, 1999.00, 1999.00),
(2, 7, 1, 599.00, 599.00),
(3, 2, 1, 14999.00, 14999.00),
(4, 9, 1, 49.90, 49.90),
(5, 5, 1, 299.00, 299.00),
(6, 1, 1, 6999.00, 6999.00),
(6, 5, 1, 299.00, 299.00),
(7, 12, 1, 128.00, 128.00),
(8, 13, 1, 399.00, 399.00),
(9, 3, 1, 1999.00, 1999.00),
(10, 10, 1, 89.00, 89.00),
(11, 14, 1, 259.00, 259.00),
(12, 1, 1, 6999.00, 6999.00),
(12, 5, 2, 299.00, 598.00),
(13, 11, 1, 168.00, 168.00),
(14, 1, 1, 6999.00, 6999.00),
(15, 5, 1, 299.00, 299.00),
(16, 2, 1, 14999.00, 14999.00),
(17, 3, 1, 1999.00, 1999.00),
(18, 9, 1, 49.90, 49.90),
(19, 6, 1, 899.00, 899.00),
(20, 12, 1, 128.00, 128.00),
(21, 13, 1, 399.00, 399.00),
(22, 14, 1, 259.00, 259.00),
(23, 7, 1, 599.00, 599.00),
(24, 4, 1, 4999.00, 4999.00),
(25, 15, 1, 79.00, 79.00),
(26, 5, 2, 99.00, 198.00),
(27, 1, 1, 6999.00, 6999.00),
(27, 2, 1, 4999.00, 4999.00),
(27, 5, 1, 299.00, 299.00),
(28, 1, 1, 6999.00, 6999.00),
(28, 5, 1, 299.00, 299.00),
(29, 1, 1, 6999.00, 6999.00),
(30, 11, 1, 168.00, 168.00),
(1, 8, 1, 99.00, 99.00),
(3, 5, 2, 299.00, 598.00),
(5, 10, 2, 89.00, 178.00),
(6, 7, 1, 599.00, 599.00),
(9, 10, 1, 89.00, 89.00),
(12, 7, 1, 599.00, 599.00),
(14, 3, 1, 1999.00, 1999.00),
(16, 10, 1, 89.00, 89.00),
(19, 5, 1, 299.00, 299.00),
(21, 15, 2, 79.00, 158.00),
(23, 8, 2, 99.00, 198.00),
(24, 3, 1, 1999.00, 1999.00),
(27, 8, 3, 99.00, 297.00),
(28, 7, 1, 599.00, 599.00),
(29, 3, 1, 1999.00, 1999.00),
(2, 8, 2, 99.00, 198.00),
(7, 9, 1, 49.90, 49.90),
(8, 10, 1, 89.00, 89.00),
(10, 11, 1, 168.00, 168.00),
(11, 13, 1, 399.00, 399.00),
(13, 9, 1, 49.90, 49.90),
(15, 7, 1, 599.00, 599.00),
(17, 14, 1, 259.00, 259.00),
(18, 10, 1, 89.00, 89.00),
(20, 11, 1, 168.00, 168.00),
(22, 13, 1, 399.00, 399.00),
(25, 15, 2, 79.00, 158.00),
(26, 7, 1, 599.00, 599.00),
(30, 9, 1, 49.90, 49.90),
(4, 15, 3, 79.00, 237.00),
(6, 8, 2, 99.00, 198.00),
(9, 5, 1, 299.00, 299.00),
(13, 6, 1, 899.00, 899.00),
(16, 7, 1, 599.00, 599.00),
(18, 13, 1, 399.00, 399.00),
(21, 10, 1, 89.00, 89.00),
(24, 11, 1, 168.00, 168.00),
(25, 12, 1, 128.00, 128.00);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and insert seed data on first startup."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
    )
    if cursor.fetchone():
        conn.close()
        return

    conn.executescript(CREATE_TABLES_SQL)
    conn.executescript(SEED_DATA_SQL)
    conn.commit()
    conn.close()


def get_schema_text() -> str:
    """Return full schema text for injection into LLM prompts."""
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    schema_parts = []
    for (table_name,) in tables:
        ddl = conn.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        ).fetchone()[0]
        schema_parts.append(ddl + ";")

        rows = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
        if rows:
            schema_parts.append(f"-- Sample rows ({table_name}):")
            for row in rows:
                schema_parts.append(f"--   {dict(row)}")

    conn.close()
    return "\n".join(schema_parts)
