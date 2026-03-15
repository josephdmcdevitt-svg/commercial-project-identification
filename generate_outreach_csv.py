"""
Generate a CSV with pre-written cold outreach emails for every target that has email.
Ready to import into any email automation tool.
"""
import json
import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_json(filename, default):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

# Load targets and company profile
targets = load_json("targets.json", [])
profile = load_json("company_profile.json", {})

# Company info (defaults if profile not filled)
COMPANY = profile.get("company_name", "Shack Shine")
CONTACT = profile.get("contact_name", "Billy")
PHONE = profile.get("contact_phone", profile.get("phone", "[PHONE]"))
EMAIL = profile.get("contact_email", profile.get("email", "[EMAIL]"))
WEBSITE = profile.get("website", "[WEBSITE]")

def get_subject(target):
    """Generate a short, direct subject line based on target type."""
    t = target.get("type", "")
    entity = target.get("entity", "")
    town = target.get("town", "")

    subjects = {
        "Municipality": f"Exterior Building Maintenance — {entity}",
        "School District": f"Summer Building Cleaning — {entity}",
        "Park District": f"Facility Exterior Maintenance — {entity}",
        "Library District": f"Building Exterior Cleaning — {entity}",
        "Township": f"Exterior Maintenance Services — {entity}",
        "HOA/Condo Association": f"Exterior Maintenance for {entity}",
        "Property Manager": f"Vendor Introduction — Commercial Exterior Cleaning",
        "Shopping Center": f"Exterior Cleaning Services — {entity}",
        "Office Park": f"Building Exterior Maintenance — {entity}",
        "Industrial Park": f"Facility Cleaning Services — {town}",
        "Apartment Complex": f"Spring Exterior Cleaning — {entity}",
        "Church/Religious": f"Campus Exterior Maintenance — {entity}",
        "Hospital/Medical": f"Facility Exterior Maintenance — {entity}",
        "Car Dealership": f"Dealership Exterior Cleaning — {entity}",
        "Hotel/Hospitality": f"Exterior Maintenance Services — {entity}",
        "Senior Living": f"Campus Exterior Cleaning — {entity}",
        "Self-Storage": f"Facility Exterior Cleaning — {entity}",
        "Other Commercial": f"Commercial Exterior Maintenance — {entity}",
    }
    return subjects.get(t, f"Commercial Exterior Cleaning — {entity}")

def get_body(target):
    """Generate a short, concise cold outreach email based on target type."""
    t = target.get("type", "")
    entity = target.get("entity", "")
    contact_name = target.get("contact", "").split(",")[0].strip() if target.get("contact") else ""

    # Greeting
    if contact_name and contact_name not in ["Purchasing", "Public Works", "Village Hall", "Facilities", "Finance Department", "Administrative Services", "City Hall", "Superintendent", "Membership", "Vendor Relations", "Property Manager"]:
        greeting = f"Hi {contact_name},"
    else:
        greeting = "Hi there,"

    # Type-specific body
    bodies = {
        "Municipality": f"""{greeting}

My name is {CONTACT} with {COMPANY}. We provide commercial power washing, window cleaning, and gutter maintenance for municipal buildings across the northern suburbs.

We're fully insured, IL EPA compliant, and experienced with government facility work. I'd like to get on your approved vendor list and learn about any upcoming maintenance needs.

Could you point me in the right direction?

{CONTACT}
{PHONE}
{EMAIL}""",

        "School District": f"""{greeting}

My name is {CONTACT} with {COMPANY}. Summer break is the perfect time for exterior building maintenance, and I'd like to offer our services to {entity}.

We handle building power washing, window cleaning, gutter cleaning, and sidewalk cleaning — and we work on compressed summer timelines.

Is there an upcoming bid cycle, or can I send over a proposal?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Park District": f"""{greeting}

My name is {CONTACT} with {COMPANY}. We provide exterior cleaning services for park district facilities — rec centers, field houses, pool buildings, and admin offices.

We're fully insured and experienced with public facility work across the northern suburbs.

Would you be open to a quick quote for your facilities?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Library District": f"""{greeting}

My name is {CONTACT} with {COMPANY}. I'd like to offer our commercial exterior cleaning services for your library building(s).

We handle power washing, window cleaning, and gutter maintenance — and we schedule around your operating hours so there's no disruption.

Can I provide a quick quote?

{CONTACT}
{PHONE}
{EMAIL}""",

        "HOA/Condo Association": f"""{greeting}

My name is {CONTACT} with {COMPANY}. We work with several HOA communities in the northern suburbs providing annual exterior maintenance — building washing, window cleaning, gutter cleaning, and walkway cleaning.

We'd love to put together a proposal for {entity}. I'm happy to attend a board meeting or do a quick property walk-through.

Would either option work?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Property Manager": f"""{greeting}

My name is {CONTACT} with {COMPANY}. We provide commercial exterior cleaning for property portfolios across the northern suburbs — power washing, windows, gutters, parking lots.

We currently service multiple commercial and residential properties in the area and would love to provide competitive quotes for your portfolio.

Would you be open to a quick call this week?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Shopping Center": f"""{greeting}

My name is {CONTACT} with {COMPANY}. Clean storefronts and walkways drive foot traffic — I'd like to offer our exterior cleaning services for {entity}.

We handle facade washing, window cleaning, sidewalk cleaning, dumpster pads, gum removal, and graffiti removal. We schedule early morning or after hours — zero disruption to tenants.

When would be a good time to walk the property?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Apartment Complex": f"""{greeting}

My name is {CONTACT} with {COMPANY}. Spring is coming and I wanted to reach out about exterior maintenance for {entity}.

We handle building washing, parking lot cleaning, window cleaning, and gutter maintenance for apartment communities across the suburbs. Annual contracts come with preferred pricing.

Can I put together a no-obligation quote?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Car Dealership": f"""{greeting}

My name is {CONTACT} with {COMPANY}. First impressions sell cars — I'd like to keep {entity} looking its best.

We handle showroom and building exterior washing, lot cleaning, service bay areas, and window cleaning. Early morning scheduling with zero disruption during business hours.

Can I provide a quick quote?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Hospital/Medical": f"""{greeting}

My name is {CONTACT} with {COMPANY}. I'd like to offer our commercial exterior cleaning services for your campus.

We're experienced with medical facility work — building washing, window cleaning, walkway cleaning, and parking structure cleaning. Fully insured and IL EPA compliant.

Who handles vendor inquiries for facilities maintenance?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Senior Living": f"""{greeting}

My name is {CONTACT} with {COMPANY}. Curb appeal and safety matter for senior communities. I'd like to offer our exterior cleaning services for {entity}.

We handle building washing, window cleaning, walkway cleaning (slip prevention), and gutter maintenance. Quiet operation and flexible scheduling around resident activities.

Would you be open to a walk-through?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Church/Religious": f"""{greeting}

My name is {CONTACT} with {COMPANY}. I'd like to offer our exterior cleaning services for your campus.

We handle building power washing, window cleaning, walkway cleaning, and parking lot cleaning. We schedule around your service times.

Can I provide a quick quote?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Office Park": f"""{greeting}

My name is {CONTACT} with {COMPANY}. I'd like to offer our commercial exterior cleaning services for {entity}.

We handle building facade washing, window cleaning, parking structure cleaning, sidewalk cleaning, and dumpster areas. Flexible scheduling with minimal disruption to tenants.

Who handles facilities maintenance for the property?

{CONTACT}
{PHONE}
{EMAIL}""",

        "Township": f"""{greeting}

My name is {CONTACT} with {COMPANY}. We provide exterior building maintenance for township facilities — offices, road garages, and community buildings.

We're fully insured and experienced with public facility work. Could I provide a quote for your buildings?

{CONTACT}
{PHONE}
{EMAIL}""",
    }

    # Default for any type not listed
    default = f"""{greeting}

My name is {CONTACT} with {COMPANY}. We provide commercial power washing, window cleaning, and gutter maintenance across the northern suburbs of Chicago.

I'd love to provide a competitive quote for {entity}. We're fully insured and IL EPA compliant.

Can I send over some information?

{CONTACT}
{PHONE}
{EMAIL}"""

    return bodies.get(t, default)

# Generate CSV
output_path = os.path.join(os.path.dirname(__file__), "outreach_ready.csv")

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Entity", "Type", "Town", "County", "Contact Name", "Email", "Phone",
        "Subject Line", "Email Body", "Priority Tier", "Est Revenue",
        "Website", "Notes", "Status"
    ])

    # Import scoring functions
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    for target in targets:
        email = target.get("email", "")
        phone = target.get("phone", "")

        # Skip if no way to contact
        if (not email or "@" not in email) and (not phone or len(phone) < 5):
            continue

        subject = get_subject(target)
        body = get_body(target)

        # Simple priority scoring
        t = target.get("type", "")
        notes = target.get("notes", "").lower()

        # Revenue estimate (simplified)
        rev_map = {
            "Municipality": 8000, "School District": 15000, "Park District": 6000,
            "Library District": 3000, "Township": 3000, "HOA/Condo Association": 5000,
            "Property Manager": 20000, "Shopping Center": 15000, "Office Park": 12000,
            "Industrial Park": 8000, "Apartment Complex": 6000, "Church/Religious": 3000,
            "Hospital/Medical": 18000, "Car Dealership": 4000, "Senior Living": 6000,
            "Self-Storage": 3000, "Other Commercial": 5000,
        }
        est_rev = rev_map.get(t, 5000)

        # Tier
        if est_rev >= 15000: tier = "A"
        elif est_rev >= 8000: tier = "B"
        elif est_rev >= 4000: tier = "C"
        else: tier = "D"

        has_email = "Yes" if email and "@" in email else "No"

        writer.writerow([
            target.get("entity", ""),
            t,
            target.get("town", ""),
            target.get("county", ""),
            target.get("contact", ""),
            email if "@" in str(email) else "",
            phone,
            subject,
            body.replace("\n", "\\n"),  # Escape newlines for CSV
            tier,
            f"${est_rev:,}",
            target.get("website", ""),
            target.get("notes", "")[:200],
            "Ready to Send" if email and "@" in email else "Phone First"
        ])

print(f"CSV generated: {output_path}")

# Count
with open(output_path, "r") as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    rows = list(reader)
    email_ready = len([r for r in rows if r[13] == "Ready to Send"])
    phone_first = len([r for r in rows if r[13] == "Phone First"])
    print(f"Total rows: {len(rows)}")
    print(f"Ready to Send (has email): {email_ready}")
    print(f"Phone First (no email): {phone_first}")
