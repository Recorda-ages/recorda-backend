import uuid

GENRE_NAMESPACE = uuid.UUID("6f1c2b8e-3d4a-4e5f-9a0b-1c2d3e4f5a6b")

GENRE_NAMES = (
    "Pop",
    "Rock",
    "Hip Hop / Rap",
    "R&B / Soul",
    "Funk",
    "Eletrônica / Dance",
    "MPB",
    "Samba / Pagode",
    "Sertanejo",
    "Forró",
    "Axé",
    "Gospel / Religioso",
    "Reggae",
    "Jazz",
    "Blues",
    "Clássica / Instrumental",
    "Trilha Sonora",
    "K-Pop",
)

GENRE_SEED = tuple((uuid.uuid5(GENRE_NAMESPACE, name), name) for name in GENRE_NAMES)
