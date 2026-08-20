from codey.database import Database
from codey.models import FileRecord
def test_database(tmp_path):
 p=tmp_path/".codey"/"index.db";r=FileRecord("main.py",".py","Python",3,"abc","1",1)
 with Database(p) as d:d.save_repository(tmp_path,False);d.upsert_files([r]);assert d.get_status()["files"]==1;d.remove_missing_files(set());assert d.get_status()["files"]==0
