from pg_guardian.seeder import (
    EVENTS_PER_CUSTOMER,
    ORDERS_PER_CUSTOMER,
    generate_demo_data,
)


def test_same_seed_gives_same_data():
    assert generate_demo_data(20, seed=1) == generate_demo_data(20, seed=1)


def test_different_seed_gives_different_data():
    assert generate_demo_data(20, seed=1) != generate_demo_data(20, seed=2)


def test_row_counts_follow_the_customer_count():
    data = generate_demo_data(10)
    assert len(data["customers"]) == 10
    assert len(data["orders"]) == 10 * ORDERS_PER_CUSTOMER
    assert len(data["audit_log"]) == 10 * EVENTS_PER_CUSTOMER


def test_emails_use_reserved_example_domains():
    data = generate_demo_data(50)
    for _name, email, _city in data["customers"]:
        assert email.endswith(("@example.com", "@example.org", "@example.net"))


def test_orders_reference_existing_customers():
    data = generate_demo_data(30)
    customer_ids = {order[0] for order in data["orders"]}
    assert customer_ids <= set(range(1, 31))
