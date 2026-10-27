from tests.conftest import seed_revlog


def test_collection_opens(col):
    assert col.sched.today >= 0


def test_seed_revlog_inserts_with_defaults(col):
    seed_revlog(col, [{"id": 1000, "cid": 1, "ease": 3}])
    assert col.db.scalar("select count() from revlog where id=1000 and usn=-1 and time=10000") == 1
