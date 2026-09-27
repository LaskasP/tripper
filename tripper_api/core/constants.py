from datetime import timedelta

GOOGLE_CERTIFICATES_URL = "https://www.googleapis.com/oauth2/v3/certs"
TRUSTED_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
INVITATION_LIFETIME = timedelta(days=7)
