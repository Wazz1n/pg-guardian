import random
from decimal import Decimal

import psycopg
from faker import Faker
from psycopg import sql

ORDERS_PER_CUSTOMER = 5
EVENTS_PER_CUSTOMER = 20


class SeedError(Exception):
    """Raised when seeding would touch data that already exists."""


def generate_demo_data(customers: int, seed: int = 42) -> dict[str, list[tuple]]:
    fake = Faker()
    fake.seed_instance(seed)
    rng = random.Random(seed)

    customer_rows = [
        (fake.name(), fake.safe_email(), fake.city()) for _ in range(customers)
    ]
    order_rows = [
        (rng.randint(1, customers), Decimal(rng.randrange(500, 50_000)) / 100)
        for _ in range(customers * ORDERS_PER_CUSTOMER)
    ]
    event_rows = [
        (fake.sentence(nb_words=6),) for _ in range(customers * EVENTS_PER_CUSTOMER)
    ]
    return {
        "customers": customer_rows,
        "orders": order_rows,
        "audit_log": event_rows,
    }


def seed_demo_data(
    dsn: str, schema: str = "pgg_demo", customers: int = 100, seed: int = 42
) -> dict[str, int]:
    data = generate_demo_data(customers, seed)
    schema_id = sql.Identifier(schema)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema,),
            )
            if cur.fetchone() is not None:
                raise SeedError(f"Schema '{schema}' already exists. Choose another name.")

            cur.execute(sql.SQL("CREATE SCHEMA {}").format(schema_id))
            cur.execute(
                sql.SQL(
                    "CREATE TABLE {}.customers ("
                    "id serial PRIMARY KEY, name text NOT NULL, "
                    "email text NOT NULL, city text NOT NULL)"
                ).format(schema_id)
            )
            cur.execute(
                sql.SQL(
                    "CREATE TABLE {}.orders ("
                    "id serial PRIMARY KEY, "
                    "customer_id integer NOT NULL REFERENCES {}.customers (id), "
                    "total numeric(10, 2) NOT NULL)"
                ).format(schema_id, schema_id)
            )
            cur.execute(
                sql.SQL("CREATE INDEX orders_customer_id_idx ON {}.orders (customer_id)").format(
                    schema_id
                )
            )
            cur.execute(
                sql.SQL(
                    "CREATE TABLE {}.audit_log ("
                    "message text NOT NULL, "
                    "created_at timestamptz NOT NULL DEFAULT now())"
                ).format(schema_id)
            )

            cur.executemany(
                sql.SQL("INSERT INTO {}.customers (name, email, city) VALUES (%s, %s, %s)").format(
                    schema_id
                ),
                data["customers"],
            )
            cur.executemany(
                sql.SQL("INSERT INTO {}.orders (customer_id, total) VALUES (%s, %s)").format(
                    schema_id
                ),
                data["orders"],
            )
            cur.executemany(
                sql.SQL("INSERT INTO {}.audit_log (message) VALUES (%s)").format(schema_id),
                data["audit_log"],
            )

    return {table: len(rows) for table, rows in data.items()}
