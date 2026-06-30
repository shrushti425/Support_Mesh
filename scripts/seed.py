import os
import sys
import asyncio
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add the parent directory to sys.path so app imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session, init_db
from app.models import Customer, Ticket

# Configure console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("supportmesh.scripts.seed")

# 10 realistic customers with varying names, emails, and account tiers
CUSTOMERS = [
    {"name": "John Doe", "email": "john.doe@example.com", "account_tier": "free"},
    {"name": "Jane Smith", "email": "jane.smith@example.com", "account_tier": "pro"},
    {"name": "Alice Johnson", "email": "alice.j@company.com", "account_tier": "enterprise"},
    {"name": "Bob Brown", "email": "bob.brown@tech.org", "account_tier": "free"},
    {"name": "Charlie Green", "email": "charlie@finance.net", "account_tier": "enterprise"},
    {"name": "David White", "email": "david.w@startup.io", "account_tier": "pro"},
    {"name": "Eva Black", "email": "eva.black@corp.com", "account_tier": "pro"},
    {"name": "Frank Miller", "email": "frank@millers.co", "account_tier": "free"},
    {"name": "Grace Hopper", "email": "grace@computing.edu", "account_tier": "enterprise"},
    {"name": "Henry Cavill", "email": "henry@geralt.uk", "account_tier": "free"}
]

# 5 sample historical tickets corresponding to some of the seeded customers above
TICKETS_RAW = [
    {
        "customer_email": "alice.j@company.com",
        "subject": "VPN connection drops every 10 mins",
        "body": "My VPN connection keeps dropping every 10 minutes when connected to the corporate gateway. It makes working remotely impossible.",
        "priority": "high",
        "classification": "technical troubleshooting",
        "status": "open",
        "draft_response": "Hi Alice,\n\nAs an Enterprise client, we've prioritized this ticket. We suggest trying to switch the OpenVPN client protocol from UDP (port 1194) to TCP (port 443) in your connection settings. This bypasses common ISP router UDP dropouts. Let us know if you want us to jump on a support call.",
        "confidence_score": 0.95,
        "latency": 1.12
    },
    {
        "customer_email": "jane.smith@example.com",
        "subject": "Need invoice to show VAT ID",
        "body": "Can you please update our invoice to include our corporate VAT number? It is EU-VAT-987654321.",
        "priority": "medium",
        "classification": "billing",
        "status": "resolved",
        "draft_response": "Hi Jane,\n\nI have updated your corporate VAT ID on your profile. You can download the updated PDF invoices by visiting Settings > Billing > Invoice History. The updated invoices are regenerated instantly.",
        "confidence_score": 0.90,
        "latency": 0.89
    },
    {
        "customer_email": "john.doe@example.com",
        "subject": "Password reset link not arriving",
        "body": "I click on forgot password but no link is sent to my email. I have been trying for hours.",
        "priority": "low",
        "classification": "password reset",
        "status": "resolved",
        "draft_response": "Hi John,\n\nWe've verified that our mail server sent the reset link. Please check your spam/promotional folders. We suggest whitelisting no-reply@supportmesh.com. If it still fails, you can try logging in again to request another email.",
        "confidence_score": 0.88,
        "latency": 0.94
    },
    {
        "customer_email": "bob.brown@tech.org",
        "subject": "How to export data?",
        "body": "Where is the button to download all my analytics data as a CSV file?",
        "priority": "low",
        "classification": "product usage",
        "status": "open",
        "draft_response": "Hi Bob,\n\nTo download your analytics data: go to Analytics > click your Custom Dashboard > select the Export options in the top-right corner. It supports both CSV and PDF formats.",
        "confidence_score": 0.85,
        "latency": 0.76
    },
    {
        "customer_email": "david.w@startup.io",
        "subject": "Double charged this month",
        "body": "My credit card was charged twice on June 1st. Please refund the duplicate charge.",
        "priority": "high",
        "classification": "refunds",
        "status": "pending",
        "draft_response": "Hi David,\n\nThanks for bringing this up. We've identified the duplicate payment. We have initiated a refund for the second transaction. It will reflect in your account within 5-10 business days depending on your bank.",
        "confidence_score": 0.92,
        "latency": 1.05
    }
]

async def seed_data():
    # Make sure tables exist
    await init_db()

    async with async_session() as session:
        logger.info("Checking if customer database is already seeded...")
        cust_stmt = select(func.count(Customer.id))
        cust_res = await session.execute(cust_stmt)
        cust_count = cust_res.scalar() or 0

        if cust_count > 0:
            logger.info(f"Database already contains {cust_count} customers. Skipping seeding.")
            return

        logger.info(f"Seeding {len(CUSTOMERS)} customers...")
        db_customers = {}
        for c in CUSTOMERS:
            db_c = Customer(
                name=c["name"],
                email=c["email"],
                account_tier=c["account_tier"]
            )
            session.add(db_c)
            db_customers[c["email"]] = db_c

        # Flush to generate UUIDs
        await session.flush()

        logger.info(f"Seeding {len(TICKETS_RAW)} historical tickets...")
        for t in TICKETS_RAW:
            cust = db_customers.get(t["customer_email"])
            if not cust:
                logger.warning(f"Customer {t['customer_email']} not found during ticket mapping. Skipping.")
                continue

            db_t = Ticket(
                customer_id=cust.id,
                subject=t["subject"],
                body=t["body"],
                priority=t["priority"],
                status=t["status"],
                classification=t["classification"],
                draft_response=t["draft_response"],
                confidence_score=t["confidence_score"],
                latency=t["latency"]
            )
            session.add(db_t)

        await session.commit()
        logger.info("Successfully seeded customers and support tickets database.")

if __name__ == "__main__":
    asyncio.run(seed_data())
