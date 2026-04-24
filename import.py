import os
import subprocess

psql = r"C:\Program Files\PostgreSQL\15\bin\psql.exe"
data_dir = r"C:\Users\user\OneDrive\Bureau\M1-IPP\S2\Database\TP\Project\musicbrainz\mbdump"
db = "musicbrainz"
user = "postgres"
password = YOUR_PASSWORD

os.environ["PGPASSWORD"] = password

tables = [
    "area_type",
    "area",
    "artist_type",
    "artist",
    "artist_credit",
    "artist_credit_name",
    "genre",
    "genre_alias",
    "language",
    "link_type",
    "link_attribute_type",
    "link",
    "l_artist_artist",
    "l_artist_recording",
    "l_artist_release_group",
    "recording",
    "release_group_primary_type",
    "release_group_secondary_type",
    "release_group",
    "release_group_secondary_type_join",
    "release_country",
    "script",
]

for table in tables:
    filepath = os.path.join(data_dir, table)
    if not os.path.exists(filepath):
        print(f"  ? {table}: file not found, skipping")
        continue

    print(f"Truncating {table}...")
    cmd_trunc = [psql, "-U", user, "-d", db, "-c", f"TRUNCATE TABLE public.{table} CASCADE;"]
    subprocess.run(cmd_trunc, capture_output=True, text=True)

    print(f"Importing {table}...")
    cmd_copy = [psql, "-U", user, "-d", db, "-c",
                f"\\copy public.{table} FROM '{filepath}'"]
    result = subprocess.run(cmd_copy, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ {table}")
    else:
        print(f"  ✗ {table}: {result.stderr.strip()}")

print("\nDone!")