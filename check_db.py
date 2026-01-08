from pathlib import Path
from eye_file.data.db import get_db_path, connect

project_root = Path(__file__).resolve().parent
db_path = get_db_path(project_root)

conn = connect(db_path)
rows = conn.execute("""
SELECT
  n.id,
  n.category_id,
  c.name AS category_name,
  n.excerpt,
  n.page_ref,
  n.created_at
FROM notes n
LEFT JOIN categories c ON c.id = n.category_id
ORDER BY n.id DESC
LIMIT 10;
""").fetchall()


print("DB:", db_path)
print("Last notes:")
for r in rows:
    print("-", r["id"], "| cat_id:", r["category_id"], "|", r["category_name"], "|", r["excerpt"], "|", r["page_ref"], "|", r["created_at"])