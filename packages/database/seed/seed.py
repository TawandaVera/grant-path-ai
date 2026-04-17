"""
Seed database with sample data for development.
Run: python -m packages.database.seed.seed
"""

import random
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from packages.database.connection import SyncDB
from packages.database.migrations.runner import run_migrations

logger = logging.getLogger("grantpath.seed")
logging.basicConfig(level=logging.INFO, format="%(message)s")

SEED_FILE = Path(__file__).parent / "grants_seed.json"


def generate_grants(count: int = 500) -> list[dict]:
    """Generate realistic sample grants."""

    funders = [
        ("National Science Foundation", "federal", "NSF"),
        ("National Institutes of Health", "federal", "NIH"),
        ("Department of Education", "federal", "ED"),
        ("USDA", "federal", "USDA"),
        ("EPA", "federal", "EPA"),
        ("Ford Foundation", "foundation", "FORD"),
        ("Gates Foundation", "foundation", "GATES"),
        ("Robert Wood Johnson Foundation", "foundation", "RWJF"),
        ("Kresge Foundation", "foundation", "KRESGE"),
        ("MacArthur Foundation", "foundation", "MAC"),
        ("W.K. Kellogg Foundation", "foundation", "KELLOGG"),
        ("New York State", "state", "NYS"),
        ("California Arts Council", "state", "CAC"),
        ("Texas Workforce Commission", "state", "TWC"),
    ]

    categories = [
        ("STEM Education", ["education", "STEM", "K-12", "workforce"]),
        ("Public Health", ["healthcare", "public health", "community health"]),
        ("Environmental Conservation", ["environment", "conservation", "climate"]),
        ("Arts & Culture", ["arts", "culture", "humanities"]),
        ("Workforce Development", ["workforce", "job training", "employment"]),
        ("Rural Development", ["rural", "agriculture", "community development"]),
        ("Youth Programs", ["youth", "education", "mentoring"]),
        ("Housing & Homelessness", ["housing", "homelessness", "social services"]),
        ("Technology & Innovation", ["technology", "innovation", "research"]),
        ("Social Justice & Equity", ["equity", "justice", "diversity"]),
        ("Mental Health", ["mental health", "behavioral health", "counseling"]),
        ("Food Security", ["food security", "nutrition", "hunger"]),
        ("Economic Development", ["economic development", "small business", "entrepreneurship"]),
        ("Disaster Preparedness", ["emergency", "disaster", "resilience"]),
        ("Senior Services", ["aging", "seniors", "elder care"]),
    ]

    states = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        None, None, None, None,  # None = no geographic restriction
    ]

    grant_types = ["Program", "Initiative", "Fund", "Award", "Grant", "Project"]
    grant_purposes = ["Innovation", "Capacity Building", "Research", "Implementation", 
                      "Planning", "Demonstration", "Expansion", "Pilot"]

    org_types_options = [
        ["nonprofit"],
        ["nonprofit", "education"],
        ["nonprofit", "education", "government"],
        ["nonprofit", "education", "government", "tribal"],
        ["small_business"],
        ["education"],
        ["nonprofit", "tribal"],
    ]

    grants = []

    for i in range(count):
        funder_name, funder_type, prefix = random.choice(funders)
        category_name, tags = random.choice(categories)
        
        # Funding amounts by funder type
        if funder_type == "federal":
            amount_min = random.choice([50000, 100000, 150000, 250000, 500000])
            amount_max = amount_min * random.choice([2, 3, 5, 10])
        elif funder_type == "foundation":
            amount_min = random.choice([10000, 25000, 50000, 75000, 100000])
            amount_max = amount_min * random.choice([2, 3, 4, 5])
        else:  # state
            amount_min = random.choice([25000, 50000, 75000, 100000])
            amount_max = amount_min * random.choice([2, 3, 4])

        deadline = datetime.now() + timedelta(days=random.randint(14, 180))
        state = random.choice(states)

        # Scoring criteria
        scoring_criteria = [
            {
                "criterion": "Statement of Need",
                "max_points": random.choice([15, 20, 25]),
                "description": "Clearly documents the problem and target population"
            },
            {
                "criterion": "Project Design/Approach",
                "max_points": random.choice([25, 30, 35]),
                "description": "Quality and feasibility of proposed activities"
            },
            {
                "criterion": "Organizational Capacity",
                "max_points": random.choice([15, 20, 25]),
                "description": "Ability to successfully implement the project"
            },
            {
                "criterion": "Evaluation Plan",
                "max_points": random.choice([10, 15, 20]),
                "description": "Methods to measure outcomes and impact"
            },
            {
                "criterion": "Budget & Sustainability",
                "max_points": random.choice([10, 15, 20]),
                "description": "Cost reasonableness and plan beyond grant period"
            },
        ]

        grant = {
            "id": f"{prefix}-2024-{i+1:05d}",
            "title": f"{category_name} {random.choice(grant_purposes)} {random.choice(grant_types)}",
            "funder_name": funder_name,
            "funder_type": funder_type,
            "description": generate_grant_description(category_name, funder_name, funder_type),
            "description_compressed": f"{funder_name} grant for {category_name.lower()}. "
                                      f"${amount_min:,}-${amount_max:,}. "
                                      f"Deadline: {deadline.strftime('%b %d, %Y')}.",
            "eligibility_criteria": generate_eligibility(funder_type, state),
            "funding_amount_min": amount_min,
            "funding_amount_max": amount_max,
            "deadline": deadline.isoformat(),
            "application_url": f"https://example.com/apply/{prefix.lower()}-2024-{i+1}",
            "category_tags": tags,
            "geographic_restrictions": [state] if state else [],
            "org_type_eligibility": random.choice(org_types_options),
            "cost_sharing_required": random.random() > 0.7,
            "cost_sharing_percentage": random.choice([10, 15, 20, 25, 50]) if random.random() > 0.7 else None,
            "scoring_criteria": scoring_criteria,
            "required_sections": [
                "executive_summary",
                "statement_of_need", 
                "project_description",
                "goals_objectives",
                "evaluation_plan",
                "organizational_capacity",
                "budget_narrative",
            ],
            "section_limits": {
                "executive_summary": random.choice([250, 300, 500]),
                "statement_of_need": random.choice([1000, 1500, 2000]),
                "project_description": random.choice([2000, 3000, 5000]),
                "goals_objectives": random.choice([500, 750, 1000]),
                "evaluation_plan": random.choice([750, 1000, 1500]),
                "organizational_capacity": random.choice([500, 750, 1000]),
                "budget_narrative": random.choice([1000, 1500, 2000]),
            },
            "status": "active",
            "source": "seed_data",
        }

        grants.append(grant)

    return grants


def generate_grant_description(category: str, funder: str, funder_type: str) -> str:
    """Generate a realistic grant description."""
    
    intros = [
        f"The {funder} invites applications for projects that advance {category.lower()}.",
        f"This funding opportunity supports innovative approaches to {category.lower()}.",
        f"{funder} is committed to strengthening {category.lower()} across communities.",
        f"Applications are sought for programs that address critical needs in {category.lower()}.",
    ]
    
    priorities = [
        "Priority will be given to projects serving underrepresented communities.",
        "Applicants should demonstrate a clear theory of change and measurable outcomes.",
        "Collaborative approaches and community partnerships are encouraged.",
        "Projects should address systemic barriers and promote equity.",
        "Innovation and scalability are key evaluation criteria.",
    ]
    
    eligibilities = {
        "federal": "Eligible applicants include state and local governments, nonprofits, institutions of higher education, and tribal organizations.",
        "foundation": "This opportunity is open to 501(c)(3) nonprofit organizations in good standing.",
        "state": "Applicants must be registered to do business in the state and demonstrate local impact.",
    }
    
    closings = [
        "Applications must be submitted through the online portal by the deadline.",
        "A letter of intent is recommended but not required.",
        "Technical assistance webinars will be offered to interested applicants.",
        "Questions should be directed to the program officer listed in the full announcement.",
    ]
    
    description = f"{random.choice(intros)} {random.choice(priorities)} "
    description += f"{eligibilities.get(funder_type, eligibilities['foundation'])} "
    description += f"{random.choice(closings)}"
    
    return description


def generate_eligibility(funder_type: str, state: str = None) -> list[str]:
    """Generate eligibility criteria."""
    
    criteria = []
    
    if funder_type == "federal":
        criteria.append("Must have a valid UEI number and active SAM.gov registration")
        criteria.append("Must not be debarred or suspended from federal awards")
    
    if funder_type == "foundation":
        criteria.append("Must be a 501(c)(3) tax-exempt organization")
        criteria.append("Must be in good standing with the IRS")
    
    if funder_type == "state":
        criteria.append(f"Must be registered to operate in {state}" if state else "Must be registered in the applicable state")
    
    # Add some common criteria
    criteria.append(f"Annual operating budget {'under \$5 million' if random.random() > 0.5 else 'of any size'}")
    criteria.append(f"At least {'2' if random.random() > 0.5 else '3'} years of organizational experience")
    
    return criteria


def generate_sample_org() -> dict:
    """Generate a sample organization for testing."""
    return {
        "id": "demo-org-001",
        "name": "Appalachian Education Alliance",
        "org_type": "nonprofit",
        "ein": "12-3456789",
        "uei": "ABC123DEF456",
        "mission_statement": (
            "Improving educational outcomes for rural communities in Appalachia through "
            "innovative STEM programming, teacher professional development, and community "
            "partnerships. We believe every child deserves access to quality education "
            "regardless of their zip code."
        ),
        "mission_short": "Improving rural education through STEM and teacher development in Appalachia.",
        "location": {
            "city": "Charleston",
            "state": "WV",
            "zip": "25301",
            "country": "US"
        },
        "annual_budget": 750000,
        "team_size": 12,
        "focus_areas": ["STEM education", "rural development", "workforce development", "youth programs"],
        "target_population": "K-12 students and teachers in rural Appalachian communities",
        "capacity_statement": (
            "Founded in 2015, AEA has served over 5,000 students across 15 rural school "
            "districts. We have successfully managed 8 federal and foundation grants "
            "totaling \$2.3M, including DOE, NSF, and the Kellogg Foundation. Our team "
            "includes 4 certified teachers, 2 PhD researchers, and experienced program managers."
        ),
        "past_grants_summary": (
            "Successfully completed: NSF ITEST (\$450K, 2022), DOE Rural Education (\$380K, 2021), "
            "Kellogg Foundation (\$250K, 2020). Current: NIH Science Education Partnership (\$500K, ongoing)."
        ),
        "indirect_cost_rate": 15.0,
    }


def generate_sample_user() -> dict:
    """Generate a sample user for testing."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    return {
        "id": str(uuid4()),
        "email": "demo@grantpathai.com",
        "password_hash": pwd_context.hash("demo123"),  # Password: demo123
        "full_name": "Demo User",
        "tier": "pro",
        "org_id": "demo-org-001",
    }


def seed_database(reset: bool = False):
    """Main seed function."""
    
    print("🌱 Seeding Grant Path AI database...")
    
    # Run migrations first
    print("📦 Running migrations...")
    run_migrations(reset=reset)
    
    with SyncDB() as db:
        # Check if already seeded
        result = db.query_one("SELECT COUNT(*) as count FROM grants")
        if result and result["count"] > 0 and not reset:
            print(f"   Database already has {result['count']} grants.")
            print("   Run with --reset to clear and re-seed.")
            return
        
        # Generate or load grants
        if SEED_FILE.exists() and not reset:
            print("   Loading grants from cache...")
            with open(SEED_FILE) as f:
                grants = json.load(f)
        else:
            print("   Generating 500 sample grants...")
            grants = generate_grants(500)
            
            # Cache for faster reseeding
            print("   Caching to grants_seed.json...")
            with open(SEED_FILE, 'w') as f:
                json.dump(grants, f, indent=2, default=str)
        
        # Insert grants
        print(f"   Inserting {len(grants)} grants...")
        for grant in grants:
            try:
                db.execute("""
                    INSERT INTO grants (
                        id, title, funder_name, funder_type, description,
                        description_compressed, eligibility_criteria, 
                        funding_amount_min, funding_amount_max, deadline,
                        application_url, category_tags, geographic_restrictions,
                        org_type_eligibility, cost_sharing_required,
                        cost_sharing_percentage, scoring_criteria, 
                        required_sections, section_limits, status, source
                    ) VALUES (
                        %(id)s, %(title)s, %(funder_name)s, %(funder_type)s, 
                        %(description)s, %(description_compressed)s,
                        %(eligibility_criteria)s, %(funding_amount_min)s,
                        %(funding_amount_max)s, %(deadline)s, %(application_url)s,
                        %(category_tags)s, %(geographic_restrictions)s,
                        %(org_type_eligibility)s, %(cost_sharing_required)s,
                        %(cost_sharing_percentage)s, %(scoring_criteria)s,
                        %(required_sections)s, %(section_limits)s, %(status)s, %(source)s
                    )
                    ON CONFLICT (id) DO NOTHING
                """, {
                    **grant,
                    "eligibility_criteria": json.dumps(grant["eligibility_criteria"]),
                    "scoring_criteria": json.dumps(grant["scoring_criteria"]),
                    "section_limits": json.dumps(grant["section_limits"]),
                })
            except Exception as e:
                logger.warning(f"Failed to insert grant {grant['id']}: {e}")
        
        # Create sample organization
        print("   Creating sample organization...")
        org = generate_sample_org()
        try:
            db.execute("""
                INSERT INTO organizations (
                    id, name, org_type, ein, uei, mission_statement, mission_short,
                    location, annual_budget, team_size, focus_areas, target_population,
                    capacity_statement, past_grants_summary, indirect_cost_rate
                ) VALUES (
                    %(id)s, %(name)s, %(org_type)s, %(ein)s, %(uei)s, 
                    %(mission_statement)s, %(mission_short)s, %(location)s,
                    %(annual_budget)s, %(team_size)s, %(focus_areas)s,
                    %(target_population)s, %(capacity_statement)s,
                    %(past_grants_summary)s, %(indirect_cost_rate)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    mission_statement = EXCLUDED.mission_statement,
                    updated_at = NOW()
            """, {
                **org,
                "location": json.dumps(org["location"]),
            })
        except Exception as e:
            logger.warning(f"Failed to create org: {e}")
        
        # Create sample user
        print("   Creating demo user (demo@grantpathai.com / demo123)...")
        user = generate_sample_user()
        user["org_id"] = org["id"]
        try:
            db.execute("""
                INSERT INTO users (id, email, password_hash, full_name, tier, org_id)
                VALUES (%(id)s, %(email)s, %(password_hash)s, %(full_name)s, %(tier)s, %(org_id)s)
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    updated_at = NOW()
            """, user)
        except Exception as e:
            logger.warning(f"Failed to create user: {e}")
        
        # Create a sample application
        print("   Creating sample application...")
        try:
            # Get a random grant
            grant = db.query_one("SELECT id FROM grants LIMIT 1")
            if grant:
                db.execute("""
                    INSERT INTO applications (
                        org_id, grant_id, project_title, status, 
                        funding_requested, notes
                    ) VALUES (
                        %(org_id)s, %(grant_id)s, %(project_title)s, 
                        %(status)s, %(funding_requested)s, %(notes)s
                    )
                    ON CONFLICT DO NOTHING
                """, {
                    "org_id": org["id"],
                    "grant_id": grant["id"],
                    "project_title": "Rural STEM Innovation Initiative",
                    "status": "drafting",
                    "funding_requested": 250000,
                    "notes": "This is a sample application for testing.",
                })
        except Exception as e:
            logger.warning(f"Failed to create application: {e}")
        
        print("")
        print("✅ Database seeded successfully!")
        print(f"   • {len(grants)} grants loaded")
        print(f"   • Sample organization: {org['name']}")
        print(f"   • Demo user: demo@grantpathai.com (password: demo123)")
        print("")
        print("   Run the app with: make dev")


if __name__ == "__main__":
    import sys
    reset = "--reset" in sys.argv
    seed_database(reset=reset)
