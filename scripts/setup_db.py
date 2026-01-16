#!/usr/bin/env python3
"""
Database Setup Script

This script initializes the database and optionally creates test data.

Usage:
    python scripts/setup_db.py          # Create tables
    python scripts/setup_db.py --reset  # Drop and recreate tables
    python scripts/setup_db.py --seed   # Add test data
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.queries import db_manager
from database.models import User, RiskAppetite
from utils.logger import logger


def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    db_manager.create_tables()
    logger.info("Tables created successfully!")


def reset_database():
    """Drop and recreate all tables."""
    logger.warning("Resetting database - all data will be lost!")
    
    confirm = input("Are you sure? Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        logger.info("Reset cancelled")
        return
    
    logger.info("Dropping all tables...")
    db_manager.drop_tables()
    
    logger.info("Recreating tables...")
    db_manager.create_tables()
    
    logger.info("Database reset complete!")


def seed_test_data():
    """Add test data to the database."""
    logger.info("Seeding test data...")
    
    # Create test users
    test_users = [
        {
            "telegram_id": 123456789,
            "username": "test_user",
            "first_name": "Test",
            "last_name": "User",
        },
        {
            "telegram_id": 987654321,
            "username": "demo_user",
            "first_name": "Demo",
        },
    ]
    
    for user_data in test_users:
        user = db_manager.get_or_create_user(**user_data)
        logger.info(f"Created user: {user.telegram_id}")
    
    # Add portfolio items for first user
    portfolios = [
        {"ticker": "RELIANCE.NS", "quantity": 10, "avg_price": 2400.0},
        {"ticker": "TCS.NS", "quantity": 5, "avg_price": 3500.0},
        {"ticker": "INFY.NS", "quantity": 15, "avg_price": 1450.0},
    ]
    
    for portfolio_data in portfolios:
        portfolio = db_manager.add_to_portfolio(123456789, **portfolio_data)
        if portfolio:
            logger.info(f"Added to portfolio: {portfolio.ticker}")
    
    # Create some price alerts
    alerts = [
        {"ticker": "RELIANCE.NS", "target_price": 2500.0, "alert_type": "above"},
        {"ticker": "TCS.NS", "target_price": 3400.0, "alert_type": "below"},
    ]
    
    for alert_data in alerts:
        alert = db_manager.create_alert(123456789, **alert_data)
        if alert:
            logger.info(f"Created alert: {alert.ticker} {alert.alert_type} {alert.target_price}")
    
    logger.info("Test data seeded successfully!")


def show_stats():
    """Show database statistics."""
    with db_manager.get_session() as session:
        from database.models import User, Portfolio, AnalysisHistory, PriceAlert
        
        users = session.query(User).count()
        portfolios = session.query(Portfolio).count()
        analyses = session.query(AnalysisHistory).count()
        alerts = session.query(PriceAlert).count()
        
        print("\n=== Database Statistics ===")
        print(f"Users:    {users}")
        print(f"Holdings: {portfolios}")
        print(f"Analyses: {analyses}")
        print(f"Alerts:   {alerts}")
        print("===========================\n")


def main():
    parser = argparse.ArgumentParser(description="Database setup script")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    parser.add_argument("--seed", action="store_true", help="Add test data")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    elif args.seed:
        create_tables()  # Ensure tables exist
        seed_test_data()
    elif args.stats:
        show_stats()
    else:
        create_tables()
    
    show_stats()


if __name__ == "__main__":
    main()
