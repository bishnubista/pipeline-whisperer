#!/usr/bin/env python3
"""
Seed database with demo experiments and outreach templates for Phase 2 testing
"""
import sys
from pathlib import Path

# Add repository paths
REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "agent-api"
sys.path.insert(0, str(APP_ROOT))

from app.models.base import SessionLocal
from app.models.experiment import Experiment
from app.models.outreach_template import OutreachTemplate

def seed_experiments():
    """Create demo A/B test experiments"""
    db = SessionLocal()

    try:
        print("🌱 Seeding experiments and templates...")

        # Experiment 1: Enterprise - Formal Tone
        exp1 = Experiment(
            experiment_id="exp_enterprise_formal_v1",
            name="Enterprise Outreach - Formal Tone",
            description="Formal, executive-level messaging for enterprise personas",
            variant="formal",
            config={
                "tone": "professional",
                "length": "concise",
                "cta": "schedule_call",
            },
            alpha=1.0,  # Thompson Sampling prior
            beta=1.0,
            is_active=True,
        )

        template1 = OutreachTemplate(
            template_id="tpl_enterprise_formal_v1",
            experiment_id="exp_enterprise_formal_v1",
            name="Enterprise Formal Email",
            description="Professional outreach for C-level/VP personas",
            subject_line="Re: {{company_name}} - Enterprise AI Opportunity",
            body_template="""Hi {{contact_name}},

I noticed {{company_name}}'s presence in {{industry}} and thought you might be interested in how we're helping similar enterprises automate their sales pipeline with AI.

Quick context: We've helped companies reduce manual lead qualification time by 70% while increasing conversion rates.

Would you be open to a brief 15-minute call next week to explore if there's a fit?

Best regards,
Pipeline Whisperer Team""",
            personalization_prompt="Keep tone professional and concise. Focus on ROI and enterprise value proposition.",
            channel="email",
            config={"follow_up_days": 3, "max_follow_ups": 2},
            is_active=True,
        )

        # Experiment 2: Enterprise - Casual Tone
        exp2 = Experiment(
            experiment_id="exp_enterprise_casual_v1",
            name="Enterprise Outreach - Casual Tone",
            description="Friendly, conversational messaging for enterprise personas",
            variant="casual",
            config={
                "tone": "friendly",
                "length": "medium",
                "cta": "quick_chat",
            },
            alpha=1.0,
            beta=1.0,
            is_active=True,
        )

        template2 = OutreachTemplate(
            template_id="tpl_enterprise_casual_v1",
            experiment_id="exp_enterprise_casual_v1",
            name="Enterprise Casual Email",
            description="Friendly outreach for C-level/VP personas",
            subject_line="Quick thought for {{company_name}}",
            body_template="""Hey {{contact_name}},

Hope this finds you well! I've been following {{company_name}} and was impressed by your work in {{industry}}.

We're building something that might be interesting for your team - basically an AI that handles the boring parts of sales outreach (scoring leads, personalizing messages, A/B testing approaches).

Curious if you'd be up for a quick 10-minute chat sometime? No pressure - just wanted to share what we're seeing work for similar companies.

Cheers,
Pipeline Whisperer Team

P.S. - We're in beta, so there might be some interesting early-adopter perks we could discuss 😊""",
            personalization_prompt="Use conversational tone, add relevant emoji, mention specific company details if available.",
            channel="email",
            config={"follow_up_days": 4, "max_follow_ups": 1},
            is_active=True,
        )

        # Experiment 3: SMB - Value-Focused
        exp3 = Experiment(
            experiment_id="exp_smb_value_v1",
            name="SMB Outreach - Value Proposition",
            description="Direct value-focused messaging for small/medium business",
            variant="value",
            config={
                "tone": "direct",
                "length": "short",
                "cta": "free_trial",
            },
            alpha=1.0,
            beta=1.0,
            is_active=True,
        )

        template3 = OutreachTemplate(
            template_id="tpl_smb_value_v1",
            experiment_id="exp_smb_value_v1",
            name="SMB Value-Focused Email",
            description="Direct value prop for SMB personas",
            subject_line="Save 10+ hours/week on sales outreach",
            body_template="""Hi {{contact_name}},

Quick question: How much time does your team spend manually reaching out to leads each week?

We built Pipeline Whisperer to automate exactly that - AI handles lead scoring, message personalization, and A/B testing so you can focus on closing deals.

Want to try it free for 14 days? No credit card required.

{{company_name}} seems like a great fit based on your industry ({{industry}}).

Let me know!

Best,
Pipeline Whisperer Team""",
            personalization_prompt="Be direct and value-focused. Highlight time savings and ease of use.",
            channel="email",
            config={"follow_up_days": 7, "max_follow_ups": 1},
            is_active=True,
        )

        # Add to database
        db.add_all([exp1, exp2, exp3])
        db.add_all([template1, template2, template3])
        db.commit()

        print("\n✅ Seeded 3 experiments:")
        print(f"  - {exp1.experiment_id}: {exp1.name}")
        print(f"  - {exp2.experiment_id}: {exp2.name}")
        print(f"  - {exp3.experiment_id}: {exp3.name}")

        print("\n✅ Seeded 3 templates:")
        print(f"  - {template1.template_id}: {template1.name}")
        print(f"  - {template2.template_id}: {template2.name}")
        print(f"  - {template3.template_id}: {template3.name}")

        print("\n🎯 Experiments are now ready for Phase 2 testing!")

    except Exception as e:
        print(f"\n❌ Error seeding experiments: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_experiments()
