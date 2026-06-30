import os
import sys
import asyncio
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add the parent directory to sys.path so app imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session, init_db
from app.models import KnowledgeBase
from app.services.rag import rag_service

# Configure console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("supportmesh.scripts.embed_knowledge")

# Define 20 high-quality synthetic knowledge base articles
ARTICLES = [
    {
        "category": "billing",
        "title": "Updating Credit Card Information",
        "content": "To update your credit card details, navigate to the Settings panel, click on the Billing tab, and select 'Update Payment Method'. Enter your new credit card details and save. The changes will apply to all subsequent billing cycles."
    },
    {
        "category": "billing",
        "title": "Failed Subscription Payments",
        "content": "If your subscription payment fails, our billing system will attempt to recharge the card 3 times over 7 days. If all attempts fail, your account tier will revert to 'free'. To avoid interruption, ensure your card has sufficient funds or update your payment details."
    },
    {
        "category": "refunds",
        "title": "Subscription Refund Policy",
        "content": "We offer a 14-day money-back guarantee for all paid subscriptions (Pro and Enterprise). If you request a cancellation within 14 days of your initial purchase or monthly renewal, we will issue a full refund to your original payment method. Contact billing@supportmesh.com to file a request."
    },
    {
        "category": "refunds",
        "title": "Requesting Refund for Double Charges",
        "content": "If you notice duplicate charges on your bank statement, please submit a refund request with screenshots of both invoice numbers and bank charges. We will process double charge refunds within 3 business days, and the funds will appear back in your account in 5-10 business days."
    },
    {
        "category": "billing",
        "title": "How to Download PDF Invoices",
        "content": "Invoices are generated on the 1st of every month. You can download pdf invoices by visiting Settings > Billing > Invoice History. Click on the download button next to any past billing period to download the receipt."
    },
    {
        "category": "billing",
        "title": "Changing Billing Details on Invoices",
        "content": "To add corporate details (such as VAT ID, Tax Code, or company address) to past or future invoices, update your corporate info in Billing Settings. Regenerated PDF invoices will immediately contain the updated information."
    },
    {
        "category": "password reset",
        "title": "Resetting a Forgotten Password",
        "content": "If you forgot your password, go to the login screen and click 'Forgot Password?'. Enter your registered email address and check your inbox. Click the temporary security link in the email, enter your new password twice, and hit confirm."
    },
    {
        "category": "password reset",
        "title": "Password Reset Link Not Arriving",
        "content": "If your password reset email does not arrive within 5 minutes: 1) Check your spam or promotional folders. 2) Whitelist no-reply@supportmesh.com. 3) Request another reset. If you still don't receive it, contact IT general support."
    },
    {
        "category": "account access",
        "title": "Two-Factor Authentication (2FA) Locked Out",
        "content": "If you lose your mobile device and cannot generate 2FA codes, you must enter one of your 10 recovery codes generated during initial setup. If you do not have recovery codes, open an account access ticket from your registered email to request manual verification."
    },
    {
        "category": "account access",
        "title": "Unlocking Suspended Accounts",
        "content": "Accounts are temporarily suspended after 5 consecutive incorrect login attempts to prevent brute-force attacks. Suspended accounts unlock automatically after 30 minutes. Alternatively, you can unlock it immediately by verifying your identity via the password reset email link."
    },
    {
        "category": "technical troubleshooting",
        "title": "Solving 'Session Expired' Login Errors",
        "content": "Frequent session expiration is caused by clock desynchronization or browser cookie corruption. Try logging out, clearing your browser cache and cookies, and verifying that your device's system time matches your timezone."
    },
    {
        "category": "technical troubleshooting",
        "title": "Social Login Integration Failures",
        "content": "If Google or GitHub login fails, check that the email of your third-party account matches your SupportMesh profile. If they differ, you must log in using your password and link the social login within the Profile Settings panel first."
    },
    {
        "category": "technical troubleshooting",
        "title": "Connecting to Corporate VPN",
        "content": "To connect to the corporate VPN: open the OpenVPN or Cisco client, enter gateway address vpn.supportmesh.com, use your SSO login credentials, and approve the 2FA push on your authentication application."
    },
    {
        "category": "technical troubleshooting",
        "title": "VPN Client Disconnection Troubleshooting",
        "content": "If your VPN disconnects frequently, check if your local router is blocking UDP port 1194 or TCP port 443. Switch to TCP protocol in your VPN client settings, disable local firewalls temporarily, or test on a different network."
    },
    {
        "category": "onboarding",
        "title": "Getting Started Guide for SupportMesh",
        "content": "Welcome to SupportMesh! To get started: 1) Configure your system settings. 2) Connect your email server. 3) Invite your team members. 4) Set up your first webhook integration. Review our onboarding checklist on the dashboard to complete set up."
    },
    {
        "category": "onboarding",
        "title": "Inviting Team Members to the Organization",
        "content": "Administrators can invite colleagues by opening Settings > Team Management. Click 'Invite Member', type their corporate email, assign a role (Admin, Agent, Billing, or Viewer), and send the invitation. Invitations are valid for 7 days."
    },
    {
        "category": "product usage",
        "title": "Creating Custom Analytics Dashboards",
        "content": "SupportMesh lets you create custom boards to track support KPIs. Go to Analytics > New Board, drag and drop widgets for volume, average response times, categories, or agent performance, and save your layout."
    },
    {
        "category": "product usage",
        "title": "Configuring Webhook Integration Settings",
        "content": "Configure outbound webhooks by visiting Settings > Webhooks > Add Webhook. Provide a target URL, select events to listen to (e.g. ticket.created, ticket.resolved), choose JSON formatting, and hit Save. You can trigger a test payload from the configuration screen."
    },
    {
        "category": "general help",
        "title": "Support Business Hours and SLA",
        "content": "SupportMesh customer support operates 24/7. Standard business support is monitored Monday through Friday 9 AM to 5 PM EST. Enterprise tier accounts receive dedicated engineers with guaranteed response SLAs under 1 hour."
    },
    {
        "category": "general help",
        "title": "Reporting System Bugs or Outages",
        "content": "To report a system bug or service interruption, submit a general support ticket with the prefix '[BUG]' in the subject. Include details of the error, steps to reproduce, and attach relevant screenshots or logs."
    }
]

async def embed_articles():
    # Make sure tables exist
    await init_db()

    async with async_session() as session:
        logger.info("Checking if knowledge base articles already exist...")
        existing_stmt = select(func.count(KnowledgeBase.id))
        res = await session.execute(existing_stmt)
        count = res.scalar() or 0

        if count > 0:
            logger.info(f"Knowledge base already contains {count} articles. Skipping seeding.")
            return

        logger.info(f"Seeding {len(ARTICLES)} knowledge base articles and computing vector embeddings...")
        
        # Load the sentence-transformer model in RAG service (lazy loaded)
        # Pre-generating embeddings
        for idx, art in enumerate(ARTICLES, 1):
            logger.info(f"[{idx}/{len(ARTICLES)}] Embedding article: '{art['title']}'...")
            
            # Combine title and content to make the vector representation richer
            combined_text = f"Title: {art['title']}\nCategory: {art['category']}\nContent: {art['content']}"
            
            embedding = await rag_service.get_embedding(combined_text)
            
            db_article = KnowledgeBase(
                title=art["title"],
                content=art["content"],
                category=art["category"],
                embedding=embedding
            )
            session.add(db_article)

        await session.commit()
        logger.info("Successfully seeded knowledge base with vector embeddings.")

if __name__ == "__main__":
    asyncio.run(embed_articles())
