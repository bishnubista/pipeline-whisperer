"""
Lightfield CRM Lead Simulator
Generates realistic lead events for demo and testing purposes
"""
import json
import random
import time
from datetime import datetime
from typing import Dict, Any
from faker import Faker

fake = Faker()

# Sample industries and company sizes
INDUSTRIES = [
    "SaaS", "E-commerce", "FinTech", "HealthTech", "EdTech",
    "Marketing", "Consulting", "Manufacturing", "Retail", "Enterprise Software"
]

COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-1000", "1000+"]

TITLES = [
    "CEO", "CTO", "VP of Engineering", "Head of Product", "Engineering Manager",
    "Product Manager", "Head of Growth", "VP of Sales", "Director of Marketing"
]


class LightfieldSimulator:
    """Generate synthetic Lightfield CRM lead events"""

    def __init__(self, seed: int | None = None):
        """Initialize simulator with optional seed for reproducibility"""
        if seed:
            Faker.seed(seed)
            random.seed(seed)

    def generate_lead(self) -> Dict[str, Any]:
        """Generate a single realistic lead"""
        company_name = fake.company()
        domain = company_name.lower().replace(" ", "").replace(",", "") + ".com"

        from datetime import timezone as tz

        lead = {
            "event_type": "lead.created",
            "timestamp": datetime.now(tz.utc).isoformat().replace("+00:00", "Z"),
            "lightfield_id": f"lf_{fake.uuid4()}",
            "company": {
                "name": company_name,
                "website": f"https://{domain}",
                "industry": random.choice(INDUSTRIES),
                "size": random.choice(COMPANY_SIZES),
                "description": fake.catch_phrase(),
            },
            "contact": {
                "name": fake.name(),
                "email": fake.email(domain=domain),
                "title": random.choice(TITLES),
                "linkedin": f"https://linkedin.com/in/{fake.user_name()}",
            },
            "source": {
                "channel": random.choice(["website", "referral", "linkedin", "conference", "webinar"]),
                "campaign": fake.word(),
                "referrer": fake.url() if random.random() > 0.5 else None,
            },
            "metadata": {
                "tech_stack": random.sample(
                    ["React", "Node.js", "Python", "Kubernetes", "AWS", "GCP", "PostgreSQL", "MongoDB"],
                    k=random.randint(2, 5)
                ),
                "pain_points": random.sample(
                    ["scalability", "performance", "cost", "reliability", "security", "compliance"],
                    k=random.randint(1, 3)
                ),
                "budget_range": random.choice(["<10k", "10k-50k", "50k-100k", "100k-500k", "500k+"]),
                "timeline": random.choice(["immediate", "1-3 months", "3-6 months", "6-12 months"]),
            },
        }

        return lead

    def generate_batch(self, count: int = 10) -> list[Dict[str, Any]]:
        """Generate multiple leads"""
        return [self.generate_lead() for _ in range(count)]

    def stream_leads(self, count: int = 100, delay_seconds: float = 2.0):
        """Generator that yields leads with delay (simulates real-time stream)"""
        for i in range(count):
            lead = self.generate_lead()
            print(f"[{i+1}/{count}] Generated lead: {lead['company']['name']} - {lead['contact']['name']}")
            yield lead
            if i < count - 1:  # Don't sleep after last lead
                time.sleep(delay_seconds)


def main():
    """Demo: generate and print sample leads"""
    simulator = LightfieldSimulator(seed=42)

    print("=" * 80)
    print("LIGHTFIELD LEAD SIMULATOR - DEMO")
    print("=" * 80)
    print()

    # Generate a few sample leads
    leads = simulator.generate_batch(3)

    for i, lead in enumerate(leads, 1):
        print(f"\n--- Lead {i} ---")
        print(json.dumps(lead, indent=2))

    print("\n" + "=" * 80)
    print(f"✅ Generated {len(leads)} sample leads")
    print("=" * 80)


if __name__ == "__main__":
    main()
