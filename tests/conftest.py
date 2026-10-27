import pytest
from anki.collection import Collection

_REVLOG_DEFAULTS = {"usn": -1, "ivl": 0, "lastIvl": 0, "factor": 0, "time": 10000, "type": 1}


@pytest.fixture
def col(tmp_path):
    c = Collection(str(tmp_path / "collection.anki2"))
    yield c
    c.close()


def seed_revlog(col, rows):
    for row in rows:
        r = {**_REVLOG_DEFAULTS, **row}
        col.db.execute(
            "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type) values (?,?,?,?,?,?,?,?,?)",
            r["id"], r["cid"], r["usn"], r["ease"], r["ivl"], r["lastIvl"], r["factor"], r["time"], r["type"],
        )
