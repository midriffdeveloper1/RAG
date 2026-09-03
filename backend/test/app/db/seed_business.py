import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.knowledge_base import Business, Holiday, OpeningHour, Service
from app.models.staff import Staff


logger = logging.getLogger(__name__)
settings = get_settings()


# Services & Pricing
SERVICES = [
    # Hair Care & Colour
    {
        "name": "Precision Haircut",
        "description": (
            "Wash, cut, blow-dry, and finish. "
            "Indicative starting price; exact pricing may vary by hair length and thickness."
        ),
        "price": 1200,
        "duration_minutes": 60,
    },
    {
        "name": "Global Hair Colour",
        "description": (
            "Ammonia-free global hair colour with gloss seal. "
            "Starting price; final pricing may vary by hair length and thickness."
        ),
        "price": 3500,
        "duration_minutes": 150,
    },
    {
        "name": "Highlights & Balayage",
        "description": (
            "Highlights and balayage hair colouring service. "
            "Starting price; exact pricing depends on hair length, thickness, and desired coverage."
        ),
        "price": 5500,
        "duration_minutes": 180,
    },
    {
        "name": "Keratin Smoothening",
        "description": (
            "Keratin-based hair smoothening treatment. "
            "Starting price; final pricing varies by hair length and thickness."
        ),
        "price": 6500,
        "duration_minutes": 210,
    },
    {
        "name": "Hair Botox Treatment",
        "description": (
            "Hair Botox treatment for smoother, healthier-looking hair. "
            "Starting price; final pricing varies by hair length and thickness."
        ),
        "price": 5000,
        "duration_minutes": 150,
    },
    {
        "name": "Restoration Hair Spa",
        "description": "90-minute scalp and hair restoration ritual.",
        "price": 2500,
        "duration_minutes": 90,
    },
    {
        "name": "Olaplex Bonding Ritual",
        "description": (
            "Olaplex bonding treatment designed to strengthen "
            "and restore damaged hair."
        ),
        "price": 2000,
        "duration_minutes": 45,
    },
    {
        "name": "Anti-Dandruff Therapy",
        "description": "Targeted scalp treatment for dandruff and scalp care.",
        "price": 1800,
        "duration_minutes": 60,
    },
    {
        "name": "Blow-Dry & Style",
        "description": "Professional blow-dry and hair styling.",
        "price": 800,
        "duration_minutes": 45,
    },

    # Skin & Facials
    {
        "name": "Gold Facial",
        "description": "Signature 24-karat gold facial treatment.",
        "price": 3800,
        "duration_minutes": 75,
    },
    {
        "name": "Hydra Facial",
        "description": (
            "Hydrating facial treatment focused on cleansing, "
            "hydration, and skin rejuvenation."
        ),
        "price": 3200,
        "duration_minutes": 60,
    },
    {
        "name": "Red Wine Facial",
        "description": (
            "Red wine-inspired facial treatment for skin "
            "rejuvenation and radiance."
        ),
        "price": 2800,
        "duration_minutes": 60,
    },
    {
        "name": "Oxy Bubble Facial",
        "description": (
            "Oxygen bubble facial treatment for cleansing "
            "and refreshed-looking skin."
        ),
        "price": 2600,
        "duration_minutes": 60,
    },
    {
        "name": "Express Clean-Up",
        "description": "Quick facial clean-up treatment for refreshed and clean skin.",
        "price": 900,
        "duration_minutes": 30,
    },
    {
        "name": "De-Tan & Bleach (Face)",
        "description": "Face de-tan and bleaching treatment.",
        "price": 700,
        "duration_minutes": 45,
    },

    # Makeup
    {
        "name": "Party & Event Makeup",
        "description": "HD or airbrush makeup for parties and events.",
        "price": 3500,
        "duration_minutes": 90,
    },
    {
        "name": "Engagement / Sangeet Makeup",
        "description": "Professional makeup for engagement and Sangeet events.",
        "price": 6000,
        "duration_minutes": 90,
    },
    {
        "name": "Bridal Trial",
        "description": "90-minute pre-wedding bridal makeup trial session.",
        "price": 4500,
        "duration_minutes": 90,
    },
    {
        "name": "The Quasar Bridal Day",
        "description": (
            "Full-day bridal package including hair, makeup, and draping."
        ),
        "price": 35000,
        "duration_minutes": 480,
    },

    # Nail Studio
    {
        "name": "Classic Manicure",
        "description": (
            "Classic manicure including nail shaping, "
            "cuticle care, and finishing."
        ),
        "price": 700,
        "duration_minutes": 40,
    },
    {
        "name": "Spa Pedicure",
        "description": "Relaxing spa pedicure treatment with foot care.",
        "price": 900,
        "duration_minutes": 50,
    },
    {
        "name": "Gel Polish",
        "description": "Professional gel polish application.",
        "price": 1200,
        "duration_minutes": 45,
    },
    {
        "name": "Acrylic / Gel Extensions",
        "description": "Acrylic or gel nail extensions.",
        "price": 2500,
        "duration_minutes": 90,
    },
    {
        "name": "Nail Art",
        "description": (
            "Custom nail art per set. "
            "Price depends on the selected design."
        ),
        "price": 500,
        "duration_minutes": 60,
    },

    # Spa & Body
    {
        "name": "Aromatherapy Massage",
        "description": (
            "Aromatherapy massage available in 60 or 90-minute sessions."
        ),
        "price": 2800,
        "duration_minutes": 90,
    },
    {
        "name": "Deep-Tissue Massage",
        "description": (
            "Deep-tissue massage focused on muscle tension and relaxation."
        ),
        "price": 3200,
        "duration_minutes": 60,
    },
    {
        "name": "Head & Shoulder Massage",
        "description": "Relaxing head and shoulder massage.",
        "price": 1200,
        "duration_minutes": 30,
    },
    {
        "name": "Hot-Stone Therapy",
        "description": (
            "Hot-stone massage therapy for relaxation and muscle relief."
        ),
        "price": 3800,
        "duration_minutes": 75,
    },
    {
        "name": "Body Polish & Scrub",
        "description": (
            "Full-body exfoliation and polishing treatment."
        ),
        "price": 2600,
        "duration_minutes": 60,
    },

    # Waxing, Threading & Eyebrow
    {
        "name": "Full-Body Waxing",
        "description": "Full-body waxing service.",
        "price": 2500,
        "duration_minutes": 90,
    },
    {
        "name": "Eyebrow Shaping",
        "description": "Professional eyebrow shaping and grooming.",
        "price": 200,
        "duration_minutes": 15,
    },
    {
        "name": "Eyebrow Tint",
        "description": (
            "Eyebrow tinting service for enhanced definition."
        ),
        "price": 400,
        "duration_minutes": 20,
    },
    {
        "name": "Upper Lip / Chin Threading or Wax",
        "description": (
            "Upper lip or chin hair removal using threading or waxing."
        ),
        "price": 100,
        "duration_minutes": 10,
    },
]


# Opening Hours
OPENING_HOURS = [
    {
        "day_of_week": "Monday",
        "open_time": "10:00",
        "close_time": "19:00",
        "is_closed": False,
    },
    {
        "day_of_week": "Tuesday",
        "open_time": "10:00",
        "close_time": "19:00",
        "is_closed": False,
    },
    {
        "day_of_week": "Wednesday",
        "open_time": "10:00",
        "close_time": "19:00",
        "is_closed": False,
    },
    {
        "day_of_week": "Thursday",
        "open_time": "10:00",
        "close_time": "19:00",
        "is_closed": False,
    },
    {
        "day_of_week": "Friday",
        "open_time": "10:00",
        "close_time": "19:00",
        "is_closed": False,
    },
    {
        "day_of_week": "Saturday",
        "open_time": "09:00",
        "close_time": "20:00",
        "is_closed": False,
    },
    {
        "day_of_week": "Sunday",
        "open_time": "11:00",
        "close_time": "17:00",
        "is_closed": False,
    },
]


# Staff
# Dummy staff data for RAG / development / testing.
STAFF = [
    {
        "name": "Ayesha Khan",
        "email": "ayesha@example.com",
        "phone": "9800000001",
        "services": [
            "Precision Haircut",
            "Global Hair Colour",
            "Highlights & Balayage",
            "Keratin Smoothening",
            "Hair Botox Treatment",
            "Restoration Hair Spa",
            "Olaplex Bonding Ritual",
            "Anti-Dandruff Therapy",
            "Blow-Dry & Style",
            "Party & Event Makeup",
            "Engagement / Sangeet Makeup",
            "Bridal Trial",
            "The Quasar Bridal Day",
        ],
    },
    {
        "name": "Rohan Mehta",
        "email": "rohan@example.com",
        "phone": "9800000002",
        "services": [
            "Precision Haircut",
            "Global Hair Colour",
            "Restoration Hair Spa",
            "Olaplex Bonding Ritual",
            "Anti-Dandruff Therapy",
            "Blow-Dry & Style",
        ],
    },
    {
        "name": "Simran Kaur",
        "email": "simran@example.com",
        "phone": "9800000003",
        "services": [
            "Gold Facial",
            "Hydra Facial",
            "Red Wine Facial",
            "Oxy Bubble Facial",
            "Express Clean-Up",
            "De-Tan & Bleach (Face)",
            "Party & Event Makeup",
            "Bridal Trial",
            "Classic Manicure",
            "Spa Pedicure",
            "Gel Polish",
            "Acrylic / Gel Extensions",
            "Nail Art",
            "Aromatherapy Massage",
            "Deep-Tissue Massage",
            "Head & Shoulder Massage",
            "Hot-Stone Therapy",
            "Body Polish & Scrub",
            "Full-Body Waxing",
            "Eyebrow Shaping",
            "Eyebrow Tint",
            "Upper Lip / Chin Threading or Wax",
        ],
    },
    {
        "name": "Neha Sharma",
        "email": "neha@example.com",
        "phone": "9800000004",
        "services": [
            "Gold Facial",
            "Hydra Facial",
            "Red Wine Facial",
            "Oxy Bubble Facial",
            "Express Clean-Up",
            "De-Tan & Bleach (Face)",
            "Party & Event Makeup",
            "Bridal Trial",
        ],
    },
    {
        "name": "Karan Singh",
        "email": "karan@example.com",
        "phone": "9800000005",
        "services": [
            "Precision Haircut",
            "Global Hair Colour",
            "Highlights & Balayage",
            "Keratin Smoothening",
            "Hair Botox Treatment",
            "Blow-Dry & Style",
            "Restoration Hair Spa",
            "Olaplex Bonding Ritual",
        ],
    },
    {
        "name": "Priya Verma",
        "email": "priya@example.com",
        "phone": "9800000006",
        "services": [
            "Classic Manicure",
            "Spa Pedicure",
            "Gel Polish",
            "Acrylic / Gel Extensions",
            "Nail Art",
        ],
    },
    {
        "name": "Manpreet Kaur",
        "email": "manpreet@example.com",
        "phone": "9800000007",
        "services": [
            "Aromatherapy Massage",
            "Deep-Tissue Massage",
            "Head & Shoulder Massage",
            "Hot-Stone Therapy",
            "Body Polish & Scrub",
        ],
    },
    {
        "name": "Arjun Malhotra",
        "email": "arjun@example.com",
        "phone": "9800000008",
        "services": [
            "Precision Haircut",
            "Blow-Dry & Style",
            "Head & Shoulder Massage",
            "Anti-Dandruff Therapy",
        ],
    },
    {
        "name": "Jasleen Gill",
        "email": "jasleen@example.com",
        "phone": "9800000009",
        "services": [
            "Full-Body Waxing",
            "Eyebrow Shaping",
            "Eyebrow Tint",
            "Upper Lip / Chin Threading or Wax",
            "Express Clean-Up",
            "De-Tan & Bleach (Face)",
        ],
    },
    {
        "name": "Riya Kapoor",
        "email": "riya@example.com",
        "phone": "9800000010",
        "services": [
            "Party & Event Makeup",
            "Engagement / Sangeet Makeup",
            "Bridal Trial",
            "The Quasar Bridal Day",
            "Blow-Dry & Style",
        ],
    },
    {
        "name": "Harpreet Singh",
        "email": "harpreet@example.com",
        "phone": "9800000011",
        "services": [
            "Deep-Tissue Massage",
            "Aromatherapy Massage",
            "Hot-Stone Therapy",
            "Head & Shoulder Massage",
            "Body Polish & Scrub",
        ],
    },
    {
        "name": "Mehak Arora",
        "email": "mehak@example.com",
        "phone": "9800000012",
        "services": [
            "Gold Facial",
            "Hydra Facial",
            "Oxy Bubble Facial",
            "Red Wine Facial",
            "Express Clean-Up",
            "Classic Manicure",
            "Spa Pedicure",
            "Gel Polish",
        ],
    },
    {
        "name": "Sahil Bedi",
        "email": "sahil@example.com",
        "phone": "9800000013",
        "services": [
            "Precision Haircut",
            "Global Hair Colour",
            "Highlights & Balayage",
            "Keratin Smoothening",
            "Hair Botox Treatment",
            "Blow-Dry & Style",
        ],
    },
    {
        "name": "Navneet Kaur",
        "email": "navneet@example.com",
        "phone": "9800000014",
        "services": [
            "Classic Manicure",
            "Spa Pedicure",
            "Gel Polish",
            "Acrylic / Gel Extensions",
            "Nail Art",
            "Eyebrow Shaping",
            "Eyebrow Tint",
        ],
    },
    {
        "name": "Ananya Joshi",
        "email": "ananya@example.com",
        "phone": "9800000015",
        "services": [
            "Party & Event Makeup",
            "Engagement / Sangeet Makeup",
            "Bridal Trial",
            "The Quasar Bridal Day",
            "Gold Facial",
            "Hydra Facial",
        ],
    },
]


# Seed Business Catalog
def seed_business_catalog() -> None:
    db: Session = SessionLocal()

    try:
        business = db.query(Business).first()

        if business is not None:
            return  

        business = Business(
            name=settings.business_name or "Quasar Salon",
            description=(
                settings.business_description
                or (
                    "Luxury salon offering hair care, hair colour, "
                    "skin and facial treatments, makeup, nail services, "
                    "spa and body treatments, waxing, threading, "
                    "eyebrow services, bridal services, and men's grooming."
                )
            ),
            address=(
                "Sector 79, Sahibzada Ajit Singh Nagar "
                "(SAS Nagar / Mohali), Punjab"
            ),
            phone="+91-9915384074",
            email="contact@salon.example",
        )

        db.add(business)
        db.flush()


        service_by_name: dict[str, Service] = {}

        for item in SERVICES:
            service = Service(
                business_id=business.id,
                **item,
            )

            db.add(service)
            service_by_name[item["name"]] = service


        for item in OPENING_HOURS:
            opening_hour = OpeningHour(
                business_id=business.id,
                **item,
            )

            db.add(opening_hour)

        db.flush()

        for item in STAFF:
            staff = Staff(
                name=item["name"],
                email=item["email"],
                phone=item["phone"],
            )

            staff.services = [
                service_by_name[service_name]
                for service_name in item["services"]
                if service_name in service_by_name
            ]

            db.add(staff)

       
        db.add(
            Holiday(
                business_id=business.id,
                day_of_week="Sunday",
                is_full_day=True,
                note="Weekly off",
            )
        )
        db.add(
            Holiday(
                business_id=business.id,
                date=date(date.today().year, 1, 26),
                is_full_day=True,
                note="Republic Day",
            )
        )

        db.commit()

        logger.info(
            "Seeded demo business catalog: %s",
            business.name,
        )

    except Exception:
        db.rollback()
        logger.exception("Failed to seed business catalog")
        raise

    finally:
        db.close()