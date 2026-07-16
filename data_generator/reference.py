"""Reference vocabularies used by the synthetic generators."""

from __future__ import annotations

SOURCE_SYSTEMS: dict[str, float] = {
    # source system -> reliability score (0-1), used later for survivorship
    "SAP_ECC": 0.92,
    "ORACLE_EBS": 0.85,
    "LEGACY_MFG": 0.65,
    "PLM_TEAMCENTER": 0.88,
    "SUPPLIER_PORTAL": 0.72,
}

UOMS: list[str] = ["EA", "KG", "G", "M", "CM", "MM", "L", "ML", "M2", "SET", "PR", "ROL"]

CURRENCIES: list[str] = ["USD", "EUR", "GBP", "INR", "CNY", "MXN"]

CATEGORIES: dict[str, dict] = {
    # category -> {uoms: plausible UOMs, price: (low, high), tier: BOM tier hint}
    "FASTENERS": {"uoms": ["EA", "SET"], "price": (0.02, 4.0), "tier": 0},
    "ELECTRONIC_COMPONENTS": {"uoms": ["EA"], "price": (0.05, 45.0), "tier": 0},
    "RAW_MATERIALS": {"uoms": ["KG", "M", "L", "ROL"], "price": (0.5, 120.0), "tier": 0},
    "SEALS_GASKETS": {"uoms": ["EA", "SET"], "price": (0.3, 25.0), "tier": 0},
    "BEARINGS": {"uoms": ["EA"], "price": (2.0, 220.0), "tier": 0},
    "CABLES_HARNESSES": {"uoms": ["EA", "M"], "price": (1.5, 90.0), "tier": 1},
    "PCB_ASSEMBLIES": {"uoms": ["EA"], "price": (15.0, 600.0), "tier": 1},
    "MACHINED_PARTS": {"uoms": ["EA"], "price": (5.0, 450.0), "tier": 1},
    "MOTORS_ACTUATORS": {"uoms": ["EA"], "price": (20.0, 1500.0), "tier": 2},
    "SUBASSEMBLIES": {"uoms": ["EA"], "price": (50.0, 3000.0), "tier": 2},
    "FINISHED_GOODS": {"uoms": ["EA"], "price": (300.0, 25000.0), "tier": 3},
}

LIFECYCLE_STATUSES: dict[str, float] = {
    # status -> sampling weight
    "ACTIVE": 0.78,
    "BLOCKED": 0.07,
    "OBSOLETE": 0.10,
    "IN_DEVELOPMENT": 0.05,
}

NOUNS: list[str] = [
    "BRACKET",
    "HOUSING",
    "SHAFT",
    "GEAR",
    "VALVE",
    "SENSOR",
    "CONNECTOR",
    "RESISTOR",
    "CAPACITOR",
    "BOLT",
    "NUT",
    "WASHER",
    "SPRING",
    "BEARING",
    "SEAL",
    "GASKET",
    "CABLE",
    "HARNESS",
    "MOTOR",
    "PUMP",
    "FILTER",
    "PANEL",
    "COVER",
    "FLANGE",
    "COUPLING",
    "RELAY",
    "SWITCH",
    "FUSE",
    "BUSHING",
    "SPACER",
    "PLATE",
    "TUBE",
]

MODIFIERS: list[str] = [
    "STAINLESS",
    "ALUMINUM",
    "BRASS",
    "NYLON",
    "HD",
    "PRECISION",
    "SEALED",
    "HIGH-TEMP",
    "LOW-PROFILE",
    "HEAVY-DUTY",
    "MINIATURE",
    "INDUSTRIAL",
    "COATED",
    "ANODIZED",
    "GALVANIZED",
    "REINFORCED",
]

SPEC_TOKENS: list[str] = [
    "M3X8",
    "M4X12",
    "M6X20",
    "M8X25",
    "10MM",
    "25MM",
    "50MM",
    "1/4IN",
    "3/8IN",
    "12V",
    "24V",
    "48V",
    "5A",
    "10A",
    "0.25W",
    "10K-OHM",
    "100UF",
    "IP67",
    "IP54",
    "6000RPM",
    "NBR-70",
    "SS316",
    "AL6061",
]

SUPPLIER_NAME_CORES: list[str] = [
    "Precision",
    "Apex",
    "Global",
    "Summit",
    "Vertex",
    "Nordic",
    "Pacific",
    "Allied",
    "Sterling",
    "Pinnacle",
    "Quantum",
    "Titan",
    "Falcon",
    "Meridian",
    "Cascade",
    "Keystone",
    "Fusion",
    "Orion",
    "Zenith",
    "Atlas",
    "Delta",
    "Sierra",
    "Vector",
    "Crown",
    "Liberty",
    "Eagle",
    "Phoenix",
    "Granite",
    "Harbor",
    "Lakeside",
]

SUPPLIER_NAME_SUFFIXES: list[str] = [
    "Components",
    "Industries",
    "Manufacturing",
    "Technologies",
    "Fasteners",
    "Electronics",
    "Metals",
    "Plastics",
    "Engineering",
    "Precision Products",
    "Supply Co",
    "Industrial Group",
]

SUPPLIER_LEGAL_FORMS: list[str] = ["Inc", "LLC", "Corp", "GmbH", "Ltd", "S.A. de C.V.", "Pvt Ltd"]

COUNTRIES_CURRENCY: list[tuple[str, str]] = [
    ("US", "USD"),
    ("US", "USD"),
    ("US", "USD"),
    ("DE", "EUR"),
    ("FR", "EUR"),
    ("GB", "GBP"),
    ("IN", "INR"),
    ("CN", "CNY"),
    ("MX", "MXN"),
]

PLANT_LOCATIONS: list[tuple[str, str, str]] = [
    ("Chicago", "US", "AMER"),
    ("Monterrey", "MX", "AMER"),
    ("Stuttgart", "DE", "EMEA"),
    ("Lyon", "FR", "EMEA"),
    ("Pune", "IN", "APAC"),
    ("Suzhou", "CN", "APAC"),
    ("Austin", "US", "AMER"),
    ("Birmingham", "GB", "EMEA"),
    ("Chennai", "IN", "APAC"),
    ("Guadalajara", "MX", "AMER"),
]

# Part-number style per source system (format realism + cross-system divergence)
PART_NUMBER_STYLES: dict[str, str] = {
    "SAP_ECC": "{cat3}-{num6}",  # e.g. FAS-104233
    "ORACLE_EBS": "{cat3}{num6}",  # e.g. FAS104233
    "LEGACY_MFG": "P/{num6}-{alpha2}",  # e.g. P/104233-AB
    "PLM_TEAMCENTER": "{cat3}-{num6}-{rev}",  # e.g. FAS-104233-A
    "SUPPLIER_PORTAL": "{alpha2}-{num6}",  # e.g. QX-104233
}
