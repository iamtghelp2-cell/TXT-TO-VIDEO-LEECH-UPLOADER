from os import environ

# API Configuration
API_ID = int(environ.get("API_ID", "0"))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

# Force Subscribe Configuration (आपका चैनल)
FORCE_SUB_CHANNEL = environ.get("FORCE_SUB_CHANNEL", "iamtghelp")
FORCE_SUB_CHANNEL_LINK = environ.get("FORCE_SUB_CHANNEL_LINK", "https://t.me/iamtghelp")

# Admin Configuration
ADMINS_RAW = environ.get("ADMINS", "")
ADMINS = [int(x) for x in ADMINS_RAW.split()] if ADMINS_RAW.strip() else []

# Optional: Bot Owner ID
OWNER_ID_RAW = environ.get("OWNER_ID", "")
OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW.strip() else None

# Database URL
DATABASE_URL = environ.get("DATABASE_URL", "")
