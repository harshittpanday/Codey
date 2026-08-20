from codey.database import Database
from codey.models import FileRecord
from codey.retrieval import retrieve
def test_retrieval(tmp_path):
 (tmp_path/"auth.py").write_text("def authenticate(user): return user")
 (tmp_path/"db.py").write_text("def connect(): pass")
 with Database(tmp_path/".codey"/"index.db") as d:d.save_repository(tmp_path,False);d.upsert_files([FileRecord("auth.py",".py","Python",1,"a","1",1),FileRecord("db.py",".py","Python",1,"b","1",1)]);r=retrieve(d,tmp_path,"Where is authenticate implemented?",2)
 assert r[0].path=="auth.py"
